"""Test fixtures. Uses TEST_DATABASE_URL (PostgreSQL) when set, otherwise a temp SQLite file."""
import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode

import httpx
import pytest
import pytest_asyncio

os.environ.setdefault("SEED_ON_START", "0")
os.environ.setdefault("RUN_BOT", "0")

from app import config, database  # noqa: E402
from app.database import Base  # noqa: E402
from app.models import Role, User  # noqa: E402
from app.security import issue_token  # noqa: E402

BOT_TOKEN = "123456:TEST"


@pytest.fixture(scope="session")
def db_url(tmp_path_factory):
    return os.getenv("TEST_DATABASE_URL") or f"sqlite+aiosqlite:///{tmp_path_factory.mktemp('db') / 'test.db'}"


@pytest_asyncio.fixture
async def db(db_url, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BOT_TOKEN", BOT_TOKEN)
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "uploads")
    database.configure(db_url)
    async with database.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await database.create_all()
    yield database
    await database.engine.dispose()


@pytest_asyncio.fixture
async def seeded(db):
    from app import seed

    async with db.SessionLocal() as s:
        await seed.run(s, demo_stock=True)
    return db


@pytest_asyncio.fixture
async def client(seeded):
    from app.main import create_app

    app = create_app()  # lifespan is not run by ASGITransport; tables are already created
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def make_user(seeded):
    counter = {"n": 1000}

    async def _make(role: Role, name: str | None = None) -> tuple[User, dict]:
        counter["n"] += 1
        async with seeded.SessionLocal() as s:
            user = User(telegram_id=counter["n"], name=name or f"{role} {counter['n']}", role=role)
            s.add(user)
            await s.commit()
            return user, {"Authorization": f"Bearer {issue_token(user)}"}

    return _make


def init_data(user_id: int, first_name: str = "Ali", token: str = BOT_TOKEN, auth_date: int | None = None) -> str:
    fields = {"auth_date": str(auth_date or int(time.time())),
              "user": json.dumps({"id": user_id, "first_name": first_name})}
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)
