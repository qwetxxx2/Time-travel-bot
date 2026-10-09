from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.config import config

engine = create_async_engine(config.DB_URL, echo=False)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    from bot.db import models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)