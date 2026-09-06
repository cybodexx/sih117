"""Hash chain verification — delegates to writer.verify_chain."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.audit.writer import verify_chain


async def verify_chain_entry(
    session: AsyncSession | None = None,
    from_id: int | None = None,
) -> dict[str, object]:
    """Verify the audit hash chain integrity."""
    return await verify_chain(session=session, from_id=from_id)
