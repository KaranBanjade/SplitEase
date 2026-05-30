from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from .config import settings

# Create engine once at import time; pool_pre_ping recycles stale connections.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Session factory – expire_on_commit=False keeps ORM objects usable after commit
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Shared declarative base (not strictly needed for text() queries, but
    keeps the door open for ORM models later)."""
    pass


async def get_db_session() -> AsyncSession:
    """Return a new AsyncSession.  Caller is responsible for closing it."""
    async with AsyncSessionLocal() as session:
        return session
