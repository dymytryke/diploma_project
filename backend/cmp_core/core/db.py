# cmp_core/core/db.py

from typing import AsyncGenerator

from cmp_core.core.config import settings
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

# 1) Створюємо движок
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
)

# 2) Фабрика сесій
AsyncSession = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


# 3) Залежність для FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession() as session:
        yield session
