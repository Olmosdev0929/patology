"""Database models.

Localized texts are stored as JSON objects: {"uz": "...", "ru": "..."}.
"""
from datetime import date, datetime, timezone
from enum import StrEnum

from sqlalchemy import (
    JSON, BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(StrEnum):
    SUPER_ADMIN = "super_admin"
    PATHOLOGIST = "pathologist"
    TECHNICIAN = "technician"
    RESIDENT = "resident"


class BiopsyStatus(StrEnum):
    REGISTERED = "registered"   # case intake done, panel being assembled
    APPROVED = "approved"       # panel approved, stock deducted, staining in progress
    REPORTED = "reported"       # final diagnosis signed out


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    username: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), default=Role.RESIDENT)
    specialty: Mapped[str | None] = mapped_column(String(200))
    cases_done: Mapped[int] = mapped_column(Integer, default=0)
    # Number of slow-moving / near-expiry markers this physician put to use.
    markers_saved: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    language: Mapped[str] = mapped_column(String(2), default="uz")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LoginToken(Base):
    """One-time token issued by the bot (/login) to open the web app outside Telegram."""
    __tablename__ = "login_tokens"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------------------------------------------------------------- Atlas

class Organ(Base):
    __tablename__ = "organs"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[dict] = mapped_column(JSONType)
    icon: Mapped[str | None] = mapped_column(String(8))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    diseases: Mapped[list["Disease"]] = relationship(back_populates="organ")


class Disease(Base):
    __tablename__ = "diseases"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    organ_id: Mapped[int] = mapped_column(ForeignKey("organs.id"))
    name: Mapped[dict] = mapped_column(JSONType)
    name_en: Mapped[str | None] = mapped_column(String(200))
    icd10: Mapped[str | None] = mapped_column(String(20))
    # {"definition": {"uz","ru"}, "clinical": ..., "gross": ..., "microscopic": ..., ...}
    sections: Mapped[dict] = mapped_column(JSONType, default=dict)
    # [{"name": "TTF-1", "result": "+"}]
    markers: Mapped[list] = mapped_column(JSONType, default=list)
    refs: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organ: Mapped[Organ] = relationship(back_populates="diseases")


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(100), unique=True)
    content_type: Mapped[str] = mapped_column(String(50))
    kind: Mapped[str] = mapped_column(String(10))          # macro | micro | ihc
    stain: Mapped[str | None] = mapped_column(String(50))  # H&E ×200, IHC DAB ×400 ...
    caption: Mapped[dict] = mapped_column(JSONType, default=dict)       # title, {uz, ru}
    description: Mapped[dict] = mapped_column(JSONType, default=dict)   # {uz, ru}
    credit: Mapped[str | None] = mapped_column(String(200))             # author / licence / "schematic"
    disease_id: Mapped[int | None] = mapped_column(ForeignKey("diseases.id", ondelete="SET NULL"))
    biopsy_id: Mapped[int | None] = mapped_column(ForeignKey("biopsies.id", ondelete="CASCADE"), index=True)
    # [{"x": 0.42, "y": 0.31, "label": {"uz": "...", "ru": "..."}}] — coordinates are 0..1 fractions
    pins: Mapped[list] = mapped_column(JSONType, default=list)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---------------------------------------------------------------- Inventory

class IgxMarker(Base):
    __tablename__ = "igx_markers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    clone: Mapped[str | None] = mapped_column(String(80))
    vendor: Mapped[str | None] = mapped_column(String(120))
    organ: Mapped[str | None] = mapped_column(String(50))     # primary organ system slug
    localization: Mapped[str | None] = mapped_column(String(30))  # nuclear | membranous | cytoplasmic | ...
    description: Mapped[dict] = mapped_column(JSONType, default=dict)
    # Names of routine markers this one is clinically paired with.
    tandem_with: Mapped[list] = mapped_column(JSONType, default=list)
    reason: Mapped[dict] = mapped_column(JSONType, default=dict)
    # {"retrieval_buffer", "retrieval_time_min", "dilution", "incubation_min", "control_tissue", "notes"}
    lab_passport: Mapped[dict] = mapped_column(JSONType, default=dict)
    # Cached aggregates, kept in sync by services.inventory
    stock: Mapped[int] = mapped_column(Integer, default=0)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    used_30d: Mapped[int] = mapped_column(Integer, default=0)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    passport_verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    passport_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    lots: Mapped[list["IgxLot"]] = relationship(
        back_populates="marker", order_by="IgxLot.expiry_date", cascade="all, delete-orphan"
    )


class IgxLot(Base):
    """A physical vial/kit. FEFO deducts from the earliest-expiring usable lot first."""
    __tablename__ = "igx_lots"

    id: Mapped[int] = mapped_column(primary_key=True)
    marker_id: Mapped[int] = mapped_column(ForeignKey("igx_markers.id", ondelete="CASCADE"), index=True)
    lot_number: Mapped[str] = mapped_column(String(80))
    expiry_date: Mapped[date] = mapped_column(Date)
    quantity: Mapped[int] = mapped_column(Integer)   # remaining tests
    received_quantity: Mapped[int] = mapped_column(Integer, default=0)  # tests in the lot on arrival
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    marker: Mapped[IgxMarker] = relationship(back_populates="lots")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    marker_id: Mapped[int] = mapped_column(ForeignKey("igx_markers.id", ondelete="CASCADE"), index=True)
    lot_id: Mapped[int | None] = mapped_column(ForeignKey("igx_lots.id", ondelete="SET NULL"))
    delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(30))  # biopsy | receive | adjust | write_off
    biopsy_id: Mapped[int | None] = mapped_column(ForeignKey("biopsies.id", ondelete="SET NULL"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


# ---------------------------------------------------------------- LIS

class Biopsy(Base):
    __tablename__ = "biopsies"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    patient_name: Mapped[str] = mapped_column(String(200))
    patient_age: Mapped[int | None] = mapped_column(Integer)
    patient_sex: Mapped[str | None] = mapped_column(String(1))
    organ: Mapped[str] = mapped_column(String(50))
    clinical_suspicion: Mapped[str | None] = mapped_column(Text)
    initial_tests: Mapped[list] = mapped_column(JSONType, default=list)
    status: Mapped[str] = mapped_column(String(20), default=BiopsyStatus.REGISTERED, index=True)
    # [{"name": "ER", "source": "routine" | "tandem" | "custom"}]
    selected_markers: Mapped[list] = mapped_column(JSONType, default=list)
    macro_text: Mapped[str | None] = mapped_column(Text)
    micro_text: Mapped[str | None] = mapped_column(Text)
    diagnosis: Mapped[str | None] = mapped_column(Text)
    scoring_result: Mapped[dict | None] = mapped_column(JSONType)
    consilium_open: Mapped[bool] = mapped_column(Boolean, default=False)
    # [{"id", "user_id", "user_name", "text", "image_ids": [], "created_at"}]
    consilium_comments: Mapped[list] = mapped_column(JSONType, default=list)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ---------------------------------------------------------------- Academy

class AnkiCard(Base):
    __tablename__ = "anki_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    deck: Mapped[str] = mapped_column(String(100), default="General")
    front_uz: Mapped[str] = mapped_column(Text, default="")
    front_ru: Mapped[str] = mapped_column(Text, default="")
    back_uz: Mapped[str] = mapped_column(Text, default="")
    back_ru: Mapped[str] = mapped_column(Text, default="")
    front_en: Mapped[str | None] = mapped_column(Text)
    sentence_id: Mapped[int | None] = mapped_column(ForeignKey("book_sentences.id", ondelete="SET NULL"))
    interval: Mapped[int] = mapped_column(Integer, default=0)        # days
    reps: Mapped[int] = mapped_column(Integer, default=0)
    easiness: Mapped[float] = mapped_column(default=2.5)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    next_review: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    category: Mapped[str | None] = mapped_column(String(100))
    author: Mapped[str | None] = mapped_column(String(300))
    pages: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str | None] = mapped_column(String(300))
    license: Mapped[str | None] = mapped_column(String(200))
    # Optional uploaded file (PDF). Stored on disk under UPLOAD_DIR/books, streamed with HTTP Range.
    file_name: Mapped[str | None] = mapped_column(String(100), unique=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    file_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    original_name: Mapped[str | None] = mapped_column(String(300))
    # Background text extraction for in-book search: none | queued | processing | ready | failed
    text_status: Mapped[str] = mapped_column(String(12), default="none")
    text_pages_done: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sentences: Mapped[list["BookSentence"]] = relationship(
        back_populates="book", order_by="BookSentence.position", cascade="all, delete-orphan"
    )


class BookPage(Base):
    """Extracted plain text of one PDF page, used for in-book search."""
    __tablename__ = "book_pages"
    __table_args__ = (UniqueConstraint("book_id", "page"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    page: Mapped[int] = mapped_column(Integer)  # 1-based
    text: Mapped[str] = mapped_column(Text, default="")


class BookProgress(Base):
    __tablename__ = "book_progress"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), primary_key=True)
    page: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class UploadSession(Base):
    """A resumable chunked upload. Bytes go to UPLOAD_DIR/tmp/<id>.part until completed."""
    __tablename__ = "upload_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(300))
    size: Mapped[int] = mapped_column(BigInteger)
    received: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class BookSentence(Base):
    __tablename__ = "book_sentences"
    __table_args__ = (UniqueConstraint("book_id", "position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    chapter: Mapped[str | None] = mapped_column(String(200))
    en: Mapped[str] = mapped_column(Text)
    uz: Mapped[str] = mapped_column(Text, default="")
    ru: Mapped[str] = mapped_column(Text, default="")
    # [{"term": "pleomorphism", "uz": "...", "ru": "..."}]
    terms: Mapped[list] = mapped_column(JSONType, default=list)

    book: Mapped[Book] = relationship(back_populates="sentences")


class AcademyMedia(Base):
    """Slides and videos linked from the academy (external URLs: YouTube, Google Slides, PDF)."""
    __tablename__ = "academy_media"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(10))  # slide | video
    title: Mapped[dict] = mapped_column(JSONType)
    description: Mapped[dict] = mapped_column(JSONType, default=dict)
    url: Mapped[str] = mapped_column(String(1000))
    author: Mapped[str | None] = mapped_column(String(200))
    organ: Mapped[str | None] = mapped_column(String(50))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    organ: Mapped[str | None] = mapped_column(String(50))
    case_text: Mapped[dict] = mapped_column(JSONType)
    options: Mapped[list] = mapped_column(JSONType)       # [{"uz","ru"}]
    correct: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[dict] = mapped_column(JSONType)
    image_id: Mapped[int | None] = mapped_column(ForeignKey("images.id", ondelete="SET NULL"))


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("quiz_questions.id", ondelete="CASCADE"))
    chosen: Mapped[int] = mapped_column(Integer)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---------------------------------------------------------------- Audit

class AuditLog(Base):
    """Append-only, hash-chained ledger: each row's hash covers the previous row's hash."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer)  # no FK: entries outlive users
    user_name: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(300))
    details: Mapped[dict | None] = mapped_column(JSONType)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)


AUDIT_IMMUTABLE_SQL = [
    """
    CREATE OR REPLACE FUNCTION audit_logs_immutable() RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'audit_logs is append-only';
    END;
    $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS audit_logs_no_change ON audit_logs",
    """
    CREATE TRIGGER audit_logs_no_change BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION audit_logs_immutable()
    """,
]
