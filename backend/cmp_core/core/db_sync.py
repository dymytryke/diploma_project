# cmp_core/core/db_sync.py

from cmp_core.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# if your async URL is e.g. "postgresql+asyncpg://…", strip the "+asyncpg"
SYNC_DATABASE_URL = settings.database_url.replace("+asyncpg", "")

# create a plain‐old SQLAlchemy Engine
engine = create_engine(
    SYNC_DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

# and a SessionLocal factory for synchronous code (Celery tasks)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
