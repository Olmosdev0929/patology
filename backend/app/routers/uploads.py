"""Resumable chunked uploads for large files (books of hundreds of MB).

Protocol:
  POST /api/uploads                     {filename, size}            -> {id, received: 0, chunk_size}
  PUT  /api/uploads/{id}?offset=N       raw bytes (<= chunk_size)   -> {received}
                                        optional X-Chunk-SHA256: checked before the chunk is accepted
  GET  /api/uploads/{id}                                            -> {received, size}  (resume point)
  DELETE /api/uploads/{id}                                          -> cancel
The finished upload is turned into a book by POST /api/books/from-upload.

Chunks are streamed straight to disk; nothing is buffered in memory beyond one network read.
"""
import hashlib
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from .. import config
from ..database import get_session
from ..models import UploadSession, User
from ..security import AdminOnly
from ..services import books

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


class UploadInit(BaseModel):
    filename: str = Field(min_length=1, max_length=300)
    size: int = Field(gt=0)


def _out(up: UploadSession) -> dict:
    return {"id": up.id, "filename": up.filename, "size": up.size, "received": up.received,
            "chunk_size": config.UPLOAD_CHUNK_MB * 1024 * 1024}


async def _own(session: AsyncSession, upload_id: str, user: User, lock: bool = False) -> UploadSession:
    up = await session.get(UploadSession, upload_id, with_for_update=lock)
    if not up or up.user_id != user.id:
        raise HTTPException(404, "Upload not found")
    return up


@router.post("", status_code=201)
async def init_upload(body: UploadInit, user: User = Depends(AdminOnly), session: AsyncSession = Depends(get_session)):
    if body.size > config.MAX_BOOK_MB * 1024 * 1024:
        raise HTTPException(413, f"File larger than {config.MAX_BOOK_MB} MB")
    if not books.has_room(body.size):  # finishing is a rename on the same volume, no second copy
        raise HTTPException(507, "Not enough free disk space on the server")
    up = UploadSession(id=uuid.uuid4().hex, user_id=user.id, filename=body.filename, size=body.size, received=0)
    session.add(up)
    books.part_path(up.id).write_bytes(b"")
    await session.commit()
    return _out(up)


@router.get("/{upload_id}")
async def upload_status(upload_id: str, user: User = Depends(AdminOnly), session: AsyncSession = Depends(get_session)):
    # Row lock: waits for an in-flight chunk of this upload to finish (or be rolled back) first,
    # so the resume point never reflects half-written bytes.
    up = await _own(session, upload_id, user, lock=True)
    on_disk = books.part_path(up.id).stat().st_size if books.part_path(up.id).exists() else 0
    if on_disk < up.received:  # bytes lost (e.g. volume restored): resume from what really exists
        up.received = on_disk
        await session.commit()
    return _out(up)


@router.put("/{upload_id}")
async def upload_chunk(upload_id: str, request: Request, offset: int = Query(ge=0),
                       x_chunk_sha256: str | None = Header(default=None),
                       user: User = Depends(AdminOnly), session: AsyncSession = Depends(get_session)):
    up = await _own(session, upload_id, user, lock=True)  # serializes chunks of one upload
    path = books.part_path(up.id)
    on_disk = path.stat().st_size if path.exists() else 0
    if offset != up.received or on_disk < offset:
        raise HTTPException(409, {"error": "offset_mismatch", "received": min(up.received, on_disk)})
    limit = min(config.UPLOAD_CHUNK_MB * 1024 * 1024, up.size - up.received)
    digest = hashlib.sha256()
    written = 0
    try:
        with path.open("r+b") as f:
            f.seek(offset)
            async for block in request.stream():
                written += len(block)
                if written > limit:
                    raise HTTPException(413, "Chunk exceeds the declared size")
                digest.update(block)
                f.write(block)
            if written == 0:
                raise HTTPException(400, "Empty chunk")
            if x_chunk_sha256 and digest.hexdigest() != x_chunk_sha256.lower():
                raise HTTPException(422, {"error": "checksum_mismatch"})
            f.truncate(offset + written)
    except BaseException:
        # Bad/oversized chunk or client gone mid-chunk: drop the partial bytes so disk and DB agree.
        with path.open("r+b") as f:
            f.truncate(offset)
        raise
    up.received = offset + written
    await session.commit()
    return _out(up)


@router.delete("/{upload_id}", status_code=204)
async def cancel_upload(upload_id: str, user: User = Depends(AdminOnly), session: AsyncSession = Depends(get_session)):
    up = await _own(session, upload_id, user)
    books.part_path(up.id).unlink(missing_ok=True)
    await session.delete(up)
    await session.commit()
