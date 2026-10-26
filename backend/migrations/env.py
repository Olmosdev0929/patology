"""Alembic environment: async engine, URL taken from the app config (DATABASE_URL)."""
import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app import config, models  # noqa: F401  (register tables)
from app.database import Base

target_metadata = Base.metadata


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata,
                      render_as_batch=connection.dialect.name == "sqlite", compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    engine = create_async_engine(config.DATABASE_URL)
    async with engine.connect() as conn:
        await conn.run_sync(_run)
        await conn.commit()
    await engine.dispose()


if context.is_offline_mode():
    context.configure(url=config.DATABASE_URL, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
elif context.config.attributes.get("connection") is not None:
    # Invoked by app.database.migrate() with an already-open connection.
    _run(context.config.attributes["connection"])
else:
    asyncio.run(_run_async())
