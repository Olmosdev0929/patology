"""Async SQLAlchemy engine and session management."""
from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from . import config


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs = {}
    engine = create_async_engine(url, **kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(engine.sync_engine, "connect")
        def _fk_on(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA foreign_keys = ON")
    return engine


engine = make_engine(config.DATABASE_URL)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def configure(url: str) -> None:
    """Point the app at a different database (used by tests)."""
    global engine
    engine = make_engine(url)
    SessionLocal.configure(bind=engine)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request, rolled back on error."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


ALEMBIC_INI = config.BASE_DIR / "alembic.ini"


def _upgrade(sync_conn) -> None:
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect

    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(config.BASE_DIR / "migrations"))
    cfg.attributes["connection"] = sync_conn
    tables = set(inspect(sync_conn).get_table_names())
    if "users" in tables and "alembic_version" not in tables:
        # Database created by an older build with create_all(): adopt it at the initial revision.
        command.stamp(cfg, "0001")
    command.upgrade(cfg, "head")


async def migrate() -> None:
    """Bring the schema to the latest Alembic revision (run on every start)."""
    from . import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(_upgrade)


async def create_all() -> None:
    """Fast schema setup for tests (production uses migrate())."""
    from . import models  # noqa: F401  (register tables)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if engine.dialect.name == "postgresql":
            # Audit log is append-only: block UPDATE/DELETE at the database level.
            for statement in models.AUDIT_IMMUTABLE_SQL:
                await conn.exec_driver_sql(statement)
