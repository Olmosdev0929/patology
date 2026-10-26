"""Slide / gross image upload, authenticated file serving and interactive pins."""
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import audit, config
from ..database import get_session
from ..models import Biopsy, Disease, Image, Role, User
from ..security import StaffOnly, current_user
from ..serializers import image_out

router = APIRouter(prefix="/api", tags=["images"])

# Detect type from file content, never from the client-supplied header.
SIGNATURES = {b"\xff\xd8\xff": ("image/jpeg", ".jpg"), b"\x89PNG\r\n\x1a\n": ("image/png", ".png")}


def sniff(head: bytes) -> tuple[str, str] | None:
    for sig, kind in SIGNATURES.items():
        if head.startswith(sig):
            return kind
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


class Pin(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    label: dict[str, str] = {}


class PinsIn(BaseModel):
    pins: list[Pin] = Field(max_length=50)


@router.post("/upload-image", status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    kind: Literal["macro", "micro", "ihc"] = Form("micro"),
    stain: str | None = Form(None),
    caption_uz: str = Form(""),
    caption_ru: str = Form(""),
    description_uz: str = Form(""),
    description_ru: str = Form(""),
    credit: str | None = Form(None),
    disease_slug: str | None = Form(None),
    biopsy_code: str | None = Form(None),
    user: User = Depends(StaffOnly),
    session: AsyncSession = Depends(get_session),
):
    data = await file.read(config.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File larger than {config.MAX_UPLOAD_MB} MB")
    detected = sniff(data[:16])
    if not detected:
        raise HTTPException(415, "Only JPEG, PNG or WebP images are accepted")
    content_type, ext = detected

    disease_id = biopsy_id = None
    if disease_slug:
        if user.role not in (Role.SUPER_ADMIN, Role.PATHOLOGIST):
            raise HTTPException(403, "Only pathologists can add atlas images")
        disease_id = (await session.execute(select(Disease.id).where(Disease.slug == disease_slug))).scalar()
        if not disease_id:
            raise HTTPException(404, "Disease not found")
    if biopsy_code:
        biopsy_id = (await session.execute(select(Biopsy.id).where(Biopsy.code == biopsy_code))).scalar()
        if not biopsy_id:
            raise HTTPException(404, "Case not found")

    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = uuid.uuid4().hex + ext
    (config.UPLOAD_DIR / filename).write_bytes(data)
    image = Image(filename=filename, content_type=content_type, kind=kind, stain=stain,
                  caption={"uz": caption_uz, "ru": caption_ru},
                  description={"uz": description_uz, "ru": description_ru}, credit=credit, disease_id=disease_id,
                  biopsy_id=biopsy_id, pins=[], uploaded_by=user.id)
    session.add(image)
    await session.flush()
    await audit.log(session, user, "image.upload", {"id": image.id, "biopsy": biopsy_code, "disease": disease_slug})
    await session.commit()
    return image_out(image)


async def _readable(session: AsyncSession, image_id: int, user: User) -> Image:
    image = await session.get(Image, image_id)
    if not image:
        raise HTTPException(404, "Image not found")
    # Case images are clinical data: staff only. Atlas images are open to every signed-in user.
    if image.biopsy_id and user.role == Role.RESIDENT:
        raise HTTPException(403, "Insufficient role")
    return image


@router.get("/images")
async def list_images(
    disease: str | None = None, biopsy: str | None = None, kind: Literal["macro", "micro", "ihc"] | None = None,
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session),
):
    q = select(Image, Disease).outerjoin(Disease, Disease.id == Image.disease_id).order_by(Image.created_at.desc(), Image.id.desc()).limit(300)
    if disease:
        q = q.where(Disease.slug == disease)
    elif biopsy:
        if user.role == Role.RESIDENT:
            raise HTTPException(403, "Insufficient role")
        q = q.join(Biopsy, Biopsy.id == Image.biopsy_id).where(Biopsy.code == biopsy)
    else:
        q = q.where(Image.biopsy_id.is_(None))  # the public gallery never mixes in clinical case images
    if kind:
        q = q.where(Image.kind == kind)
    return [image_out(i, d) for i, d in (await session.execute(q)).all()]


@router.get("/images/{image_id}/file")
async def image_file(image_id: int, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    image = await _readable(session, image_id, user)
    path = config.UPLOAD_DIR / image.filename
    if not path.exists():
        raise HTTPException(404, "File missing")
    return FileResponse(path, media_type=image.content_type, headers={"Cache-Control": "private, max-age=3600"})


@router.put("/images/{image_id}/pins")
async def set_pins(image_id: int, body: PinsIn, user: User = Depends(StaffOnly), session: AsyncSession = Depends(get_session)):
    image = await _readable(session, image_id, user)
    if user.role not in (Role.SUPER_ADMIN, Role.PATHOLOGIST):
        raise HTTPException(403, "Only pathologists can annotate")
    image.pins = [p.model_dump() for p in body.pins]
    await audit.log(session, user, "image.pins", {"id": image_id, "count": len(body.pins)})
    await session.commit()
    return image_out(image)
