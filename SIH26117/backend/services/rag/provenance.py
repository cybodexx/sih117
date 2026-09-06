"""Citation resolution: chunk IDs → document metadata for grounding."""
from __future__ import annotations

import uuid

from pydantic import BaseModel

from backend.db.base import async_session
from backend.db.models.chunk_ref import ChunkRefModel
from backend.db.models.document import DocumentModel


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    page: int
    bbox: list[float]
    snippet: str


async def resolve(chunk_ids: list[str]) -> list[Citation]:
    """Resolve chunk IDs to citation objects with document metadata."""
    if not chunk_ids:
        return []

    async with async_session() as session:
        from sqlalchemy import select

        stmt = (
            select(ChunkRefModel, DocumentModel.filename)
            .join(DocumentModel, ChunkRefModel.document_id == DocumentModel.id)
            .where(ChunkRefModel.id.in_([uuid.UUID(cid) for cid in chunk_ids]))
        )
        result = await session.execute(stmt)
        rows = result.all()

    citations: list[Citation] = []
    for ref, title in rows:
        citations.append(
            Citation(
                chunk_id=str(ref.id),
                document_id=str(ref.document_id),
                title=title,
                page=ref.page_start,
                bbox=ref.bbox if ref.bbox else [],
                snippet=ref.text_preview[:200] if ref.text_preview else "",
            )
        )
    return citations
