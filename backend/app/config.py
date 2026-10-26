"""Application settings loaded from environment variables."""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent
load_dotenv(ROOT_DIR / ".env")


def _ids(name: str) -> set[int]:
    raw = os.getenv(name, "").replace(" ", "")
    return {int(x) for x in raw.split(",") if x}


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres@localhost:5432/pathouz")
    # Railway/Heroku give "postgres://" or "postgresql://" — switch to the async driver.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix):]
    return url


DATABASE_URL = _database_url()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "").lstrip("@")
WEBAPP_URL = os.getenv("WEBAPP_URL", "").rstrip("/")
# Telegram IDs that are always promoted to super_admin on login.
SUPER_ADMIN_IDS = _ids("SUPER_ADMIN_IDS")
JWT_TTL_HOURS = int(os.getenv("JWT_TTL_HOURS", "12"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", ROOT_DIR / "data" / "uploads"))
def _jwt_secret() -> str:
    """Use JWT_SECRET, else a random secret persisted next to the uploads so sessions survive restarts."""
    if os.getenv("JWT_SECRET"):
        return os.environ["JWT_SECRET"]
    path = UPLOAD_DIR.parent / ".jwt_secret"
    try:
        if path.exists():
            return path.read_text().strip()
        path.parent.mkdir(parents=True, exist_ok=True)
        value = secrets.token_urlsafe(48)
        path.write_text(value)
        path.chmod(0o600)
        return value
    except OSError:
        return secrets.token_urlsafe(48)


JWT_SECRET = _jwt_secret()
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "15"))          # images
MAX_BOOK_MB = int(os.getenv("MAX_BOOK_MB", "2048"))           # whole PDF book
UPLOAD_CHUNK_MB = int(os.getenv("UPLOAD_CHUNK_MB", "16"))     # max size of one chunk request
UPLOAD_TTL_HOURS = int(os.getenv("UPLOAD_TTL_HOURS", "48"))   # unfinished uploads are purged after this
DISK_RESERVE_MB = int(os.getenv("DISK_RESERVE_MB", "512"))    # never fill the volume past this
PDF_WORKER_MEM_MB = int(os.getenv("PDF_WORKER_MEM_MB", "1024"))  # address-space cap of the text worker
PDF_WORKER_TIMEOUT_S = int(os.getenv("PDF_WORKER_TIMEOUT_S", "600"))
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", ROOT_DIR / "frontend" / "dist"))
PORT = int(os.getenv("PORT", "8000"))
SEED_ON_START = os.getenv("SEED_ON_START", "1") == "1"
RUN_BOT = os.getenv("RUN_BOT", "1") == "1"
# Local development only: allows /api/auth/dev-login without Telegram.
DEV_MODE = os.getenv("DEV_MODE", "0") == "1"

# Inventory thresholds
EXPIRY_WARNING_DAYS = int(os.getenv("EXPIRY_WARNING_DAYS", "60"))
SLOW_MOVER_MAX_30D = int(os.getenv("SLOW_MOVER_MAX_30D", "5"))
FAST_MOVER_MIN_30D = int(os.getenv("FAST_MOVER_MIN_30D", "20"))
LOW_STOCK_TESTS = int(os.getenv("LOW_STOCK_TESTS", "10"))
