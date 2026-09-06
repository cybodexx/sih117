from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.base import async_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends-compatible async generator that yields a DB session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
