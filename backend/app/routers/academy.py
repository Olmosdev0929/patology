"""Smart Academy: books (parallel reader + large PDFs), SM-2 flashcards and the daily quiz."""
import asyncio
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import audit
from ..database import get_session
from ..models import (
    AcademyMedia, AnkiCard, Book, BookPage, BookProgress, BookSentence, QuizAttempt, QuizQuestion, Role, UploadSession, User,
)
from ..security import AdminOnly, PathologistOnly, current_user
from ..serializers import card_out
from ..services import books as books_service
from ..services import sm2

router = APIRouter(prefix="/api", tags=["academy"])

DAILY_QUIZ_SIZE = 5


# ---------------------------------------------------------------- Reader

class SentenceIn(BaseModel):
    en: str = Field(min_length=1)
    uz: str = ""
    ru: str = ""
    chapter: str | None = None
    terms: list[dict[str, str]] = []


class BookImport(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    category: str | None = None
    author: str | None = None
    pages: int | None = Field(default=None, ge=1)
    source: str | None = None
    license: str = Field(min_length=1, description="Rights under which the text is used")
    sentences: list[SentenceIn] = Field(min_length=1)


def _book_out(b: Book, sentences: int = 0, chapters: int = 0, progress: int | None = None) -> dict:
    return {
        "id": b.id, "title": b.title, "category": b.category, "author": b.author, "pages": b.pages,
        "source": b.source, "license": b.license, "sentences": sentences, "chapters": chapters,
        "has_file": bool(b.file_name), "file_size": b.file_size, "original_name": b.original_name,
        "text_status": b.text_status, "text_pages_done": b.text_pages_done, "progress_page": progress,
        "file_url": f"/api/books/{b.id}/file" if b.file_name else None,
    }


@router.get("/books")
async def books(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(Book, func.count(BookSentence.id), func.count(func.distinct(BookSentence.chapter)))
        .outerjoin(BookSentence).group_by(Book.id).order_by(Book.id)
    )).all()
    progress = dict((await session.execute(
        select(BookProgress.book_id, BookProgress.page).where(BookProgress.user_id == user.id)
    )).all())
    return [_book_out(b, n, ch, progress.get(b.id)) for b, n, ch in rows]


@router.get("/books/{book_id}")
async def book(book_id: int, offset: int = 0, limit: int = Query(50, le=200),
               user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    b = await session.get(Book, book_id)
    if not b:
        raise HTTPException(404, "Book not found")
    total = (await session.execute(select(func.count()).where(BookSentence.book_id == book_id))).scalar()
    rows = (await session.execute(
        select(BookSentence).where(BookSentence.book_id == book_id)
        .order_by(BookSentence.position).offset(offset).limit(limit)
    )).scalars()
    progress = await session.get(BookProgress, (user.id, book_id))
    return {
        **_book_out(b, total, 0, progress.page if progress else None), "total": total,
        "sentences": [{"id": s.id, "position": s.position, "chapter": s.chapter, "en": s.en, "uz": s.uz,
                       "ru": s.ru, "terms": s.terms} for s in rows],
    }


class BookFromUpload(BaseModel):
    upload_id: str
    title: str = Field(min_length=1, max_length=300)
    category: str | None = Field(default=None, max_length=100)
    author: str | None = Field(default=None, max_length=300)
    source: str | None = Field(default=None, max_length=300)
    license: str = Field(min_length=1, max_length=200, description="Rights under which the file is shared")


@router.post("/books/from-upload", status_code=201)
async def book_from_upload(body: BookFromUpload, user: User = Depends(AdminOnly),
                           session: AsyncSession = Depends(get_session)):
    up = await session.get(UploadSession, body.upload_id, with_for_update=True)
    if not up or up.user_id != user.id:
        raise HTTPException(404, "Upload not found")
    part = books_service.part_path(up.id)
    if up.received != up.size or not part.exists() or part.stat().st_size != up.size:
        raise HTTPException(409, {"error": "upload_incomplete", "received": up.received, "size": up.size})
    if not books_service.looks_like_pdf(part):
        raise HTTPException(415, "Only PDF books are supported")
    digest = await asyncio.to_thread(books_service.sha256_of, part)
    duplicate = (await session.execute(select(Book.id).where(Book.file_sha256 == digest))).scalar()
    if duplicate:
        raise HTTPException(409, {"error": "duplicate", "book_id": duplicate})

    file_name = f"{uuid.uuid4().hex}.pdf"
    # Same volume, so this is an atomic rename rather than a copy of hundreds of MB.
    await asyncio.to_thread(part.replace, books_service.books_dir() / file_name)
    b = Book(title=body.title, category=body.category, author=body.author, source=body.source, license=body.license,
             file_name=file_name, file_size=up.size, file_sha256=digest, original_name=up.filename,
             text_status="queued", uploaded_by=user.id)
    session.add(b)
    await session.delete(up)
    await session.flush()
    await audit.log(session, user, "book.upload", {"title": b.title, "mb": round(up.size / 1048576, 1)})
    await session.commit()
    books_service.schedule_extraction(b.id)
    return _book_out(b)


@router.get("/books/{book_id}/file")
async def book_file(book_id: int, _: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    """Streams the PDF. Range requests are honoured, so the viewer only fetches the pages it shows."""
    b = await session.get(Book, book_id)
    if not b or not b.file_name:
        raise HTTPException(404, "Book file not found")
    path = books_service.book_path(b)
    if not path.exists():
        raise HTTPException(404, "Book file missing on server")
    return FileResponse(path, media_type="application/pdf", headers={
        "Cache-Control": "private, max-age=86400",
        "Content-Disposition": f"inline; filename=\"book-{b.id}.pdf\"",
    })


@router.get("/books/{book_id}/search")
async def book_search(book_id: int, q: str = Query(min_length=2, max_length=100), limit: int = Query(30, le=100),
                      _: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    like = f"%{q.lower()}%"
    rows = (await session.execute(
        select(BookPage.page, BookPage.text).where(BookPage.book_id == book_id, func.lower(BookPage.text).like(like))
        .order_by(BookPage.page).limit(limit)
    )).all()
    hits = []
    for page, text in rows:
        i = text.lower().find(q.lower())
        start = max(0, i - 80)
        hits.append({"page": page, "snippet": ("…" if start else "") + text[start:i + len(q) + 120].replace("\n", " ") + "…"})
    return hits


class ProgressIn(BaseModel):
    page: int = Field(ge=1)


@router.put("/books/{book_id}/progress")
async def save_progress(book_id: int, body: ProgressIn, user: User = Depends(current_user),
                        session: AsyncSession = Depends(get_session)):
    if not await session.get(Book, book_id):
        raise HTTPException(404, "Book not found")
    row = await session.get(BookProgress, (user.id, book_id))
    if row:
        row.page = body.page
    else:
        session.add(BookProgress(user_id=user.id, book_id=book_id, page=body.page))
    await session.commit()
    return {"page": body.page}


@router.post("/books/{book_id}/reindex", status_code=202)
async def reindex_book(book_id: int, _: User = Depends(AdminOnly), session: AsyncSession = Depends(get_session)):
    b = await session.get(Book, book_id)
    if not b or not b.file_name:
        raise HTTPException(404, "Book file not found")
    b.text_status = "queued"
    await session.commit()
    books_service.schedule_extraction(b.id)
    return {"text_status": "queued"}


@router.delete("/books/{book_id}", status_code=204)
async def delete_book(book_id: int, user: User = Depends(AdminOnly), session: AsyncSession = Depends(get_session)):
    b = await session.get(Book, book_id)
    if not b:
        raise HTTPException(404, "Book not found")
    path = books_service.book_path(b) if b.file_name else None
    await session.delete(b)
    await audit.log(session, user, "book.delete", {"title": b.title})
    await session.commit()
    if path:
        path.unlink(missing_ok=True)


@router.post("/books/import", status_code=201)
async def import_book(body: BookImport, user: User = Depends(AdminOnly), session: AsyncSession = Depends(get_session)):
    b = Book(title=body.title, category=body.category, author=body.author, pages=body.pages,
             source=body.source, license=body.license)
    b.sentences = [BookSentence(position=i, **s.model_dump()) for i, s in enumerate(body.sentences)]
    session.add(b)
    await session.flush()
    await audit.log(session, user, "book.import", {"title": b.title, "sentences": len(body.sentences)})
    await session.commit()
    return {"id": b.id}


# ---------------------------------------------------------------- Slides & videos

class MediaIn(BaseModel):
    kind: str = Field(pattern="^(slide|video)$")
    title: dict[str, str]
    description: dict[str, str] = {}
    url: str = Field(pattern=r"^https://", max_length=1000)
    author: str | None = Field(default=None, max_length=200)
    organ: str | None = None


def _media_out(m: AcademyMedia) -> dict:
    return {"id": m.id, "kind": m.kind, "title": m.title, "description": m.description, "url": m.url,
            "author": m.author, "organ": m.organ, "created_at": m.created_at.isoformat()}


@router.get("/media")
async def list_media(kind: str | None = Query(None, pattern="^(slide|video)$"),
                     _: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    q = select(AcademyMedia).order_by(AcademyMedia.created_at.desc())
    if kind:
        q = q.where(AcademyMedia.kind == kind)
    return [_media_out(m) for m in (await session.execute(q)).scalars()]


@router.post("/media", status_code=201)
async def add_media(body: MediaIn, user: User = Depends(PathologistOnly), session: AsyncSession = Depends(get_session)):
    m = AcademyMedia(**body.model_dump(), created_by=user.id)
    session.add(m)
    await session.flush()
    await audit.log(session, user, "media.add", {"kind": m.kind, "url": m.url})
    await session.commit()
    return _media_out(m)


@router.delete("/media/{media_id}", status_code=204)
async def delete_media(media_id: int, user: User = Depends(PathologistOnly), session: AsyncSession = Depends(get_session)):
    m = await session.get(AcademyMedia, media_id)
    if not m:
        raise HTTPException(404, "Not found")
    if m.created_by != user.id and user.role != Role.SUPER_ADMIN:
        raise HTTPException(403, "Only the author or an admin can remove this")
    await session.delete(m)
    await audit.log(session, user, "media.delete", {"id": media_id})
    await session.commit()


# ---------------------------------------------------------------- Anki (SM-2)

class CardIn(BaseModel):
    deck: str = Field(default="General", max_length=100)
    front_uz: str = ""
    front_ru: str = ""
    back_uz: str = ""
    back_ru: str = ""
    front_en: str | None = None
    sentence_id: int | None = None


class ReviewIn(BaseModel):
    answer: str = Field(pattern="^(again|hard|good|easy)$")


async def _own_card(session: AsyncSession, card_id: int, user: User) -> AnkiCard:
    card = await session.get(AnkiCard, card_id, with_for_update=True)
    if not card or card.user_id != user.id:
        raise HTTPException(404, "Card not found")
    return card


@router.get("/anki")
async def list_cards(due: bool = False, deck: str | None = None,
                     user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    q = select(AnkiCard).where(AnkiCard.user_id == user.id).order_by(AnkiCard.next_review, AnkiCard.id)
    if due:
        q = q.where(AnkiCard.next_review <= date.today())
    if deck:
        q = q.where(AnkiCard.deck == deck)
    return [card_out(c) for c in (await session.execute(q)).scalars()]


@router.get("/anki/stats")
async def card_stats(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    base = select(func.count()).where(AnkiCard.user_id == user.id)
    total = (await session.execute(base)).scalar()
    due = (await session.execute(base.where(AnkiCard.next_review <= date.today()))).scalar()
    learned = (await session.execute(base.where(AnkiCard.interval >= 21))).scalar()
    decks = (await session.execute(
        select(AnkiCard.deck, func.count()).where(AnkiCard.user_id == user.id).group_by(AnkiCard.deck)
    )).all()
    return {"total": total, "due": due, "mature": learned, "decks": [{"deck": d, "count": n} for d, n in decks]}


@router.post("/anki", status_code=201)
async def create_card(body: CardIn, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    data = body.model_dump()
    if body.sentence_id:
        # One-click card from the parallel reader: English on the front, translations on the back.
        s = await session.get(BookSentence, body.sentence_id)
        if not s:
            raise HTTPException(404, "Sentence not found")
        data["front_en"] = data["front_en"] or s.en
        data["front_uz"] = data["front_uz"] or s.en
        data["front_ru"] = data["front_ru"] or s.en
        data["back_uz"] = data["back_uz"] or s.uz
        data["back_ru"] = data["back_ru"] or s.ru
    if not (data["front_uz"] or data["front_ru"]):
        raise HTTPException(422, "Card front is empty")
    card = AnkiCard(user_id=user.id, **data)
    session.add(card)
    await session.commit()
    return card_out(card)


@router.post("/anki/{card_id}/review")
async def review_card(card_id: int, body: ReviewIn, user: User = Depends(current_user),
                      session: AsyncSession = Depends(get_session)):
    card = await _own_card(session, card_id, user)
    state, next_day = sm2.review(sm2.CardState(card.interval, card.reps, card.easiness, card.lapses), body.answer)
    card.interval, card.reps, card.easiness, card.lapses = state.interval, state.reps, state.easiness, state.lapses
    card.next_review = next_day
    await session.commit()
    return card_out(card)


@router.delete("/anki/{card_id}", status_code=204)
async def delete_card(card_id: int, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    await session.delete(await _own_card(session, card_id, user))
    await session.commit()


# ---------------------------------------------------------------- Daily quiz

def _question_out(q: QuizQuestion) -> dict:
    return {"id": q.id, "organ": q.organ, "case_text": q.case_text, "options": q.options, "image_id": q.image_id}


@router.get("/quiz/daily")
async def daily_quiz(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    """Same set for everyone on a given day, rotating through the question bank."""
    ids = (await session.execute(select(QuizQuestion.id).order_by(QuizQuestion.id))).scalars().all()
    if not ids:
        return {"date": date.today().isoformat(), "questions": [], "answered": {}}
    start = (date.today().toordinal() * DAILY_QUIZ_SIZE) % len(ids)
    todays = [ids[(start + i) % len(ids)] for i in range(min(DAILY_QUIZ_SIZE, len(ids)))]
    questions = {q.id: q for q in (await session.execute(select(QuizQuestion).where(QuizQuestion.id.in_(todays)))).scalars()}
    answered = {
        a.question_id: {"chosen": a.chosen, "correct": a.is_correct}
        for a in (await session.execute(select(QuizAttempt).where(
            QuizAttempt.user_id == user.id, QuizAttempt.question_id.in_(todays),
            func.date(QuizAttempt.created_at) == date.today(),
        ))).scalars()
    }
    return {"date": date.today().isoformat(), "questions": [_question_out(questions[i]) for i in todays], "answered": answered}


class AnswerIn(BaseModel):
    chosen: int = Field(ge=0)


@router.post("/quiz/{question_id}/answer")
async def answer(question_id: int, body: AnswerIn, user: User = Depends(current_user),
                 session: AsyncSession = Depends(get_session)):
    q = await session.get(QuizQuestion, question_id)
    if not q:
        raise HTTPException(404, "Question not found")
    if body.chosen >= len(q.options):
        raise HTTPException(422, "Invalid option")
    ok = body.chosen == q.correct
    session.add(QuizAttempt(user_id=user.id, question_id=q.id, chosen=body.chosen, is_correct=ok))
    await session.commit()
    return {"correct": ok, "correct_index": q.correct, "explanation": q.explanation}


@router.get("/quiz/stats")
async def quiz_stats(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    total, correct = (await session.execute(
        select(func.count(), func.coalesce(func.sum(case((QuizAttempt.is_correct, 1), else_=0)), 0))
        .where(QuizAttempt.user_id == user.id)
    )).one()
    return {"answered": total, "correct": int(correct)}


class QuestionIn(BaseModel):
    organ: str | None = None
    case_text: dict[str, str]
    options: list[dict[str, str]] = Field(min_length=2, max_length=6)
    correct: int = Field(ge=0)
    explanation: dict[str, str] = {}


@router.post("/quiz", status_code=201)
async def add_question(body: QuestionIn, user: User = Depends(PathologistOnly), session: AsyncSession = Depends(get_session)):
    if body.correct >= len(body.options):
        raise HTTPException(422, "correct must point to one of the options")
    if not (body.case_text.get("uz") or body.case_text.get("ru")):
        raise HTTPException(422, "Question text is required")
    q = QuizQuestion(**body.model_dump())
    session.add(q)
    await session.flush()
    await audit.log(session, user, "quiz.add", {"id": q.id})
    await session.commit()
    return {"id": q.id}
