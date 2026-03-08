from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import Settings


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Database:
    def __init__(self, settings: Settings) -> None:
        self.engine = create_async_engine(settings.database_url, echo=False, future=True)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def create_all(self) -> None:
        from database.models import Base as ModelBase

        async with self.engine.begin() as conn:
            await conn.run_sync(ModelBase.metadata.create_all)

    async def dispose(self) -> None:
        await self.engine.dispose()
