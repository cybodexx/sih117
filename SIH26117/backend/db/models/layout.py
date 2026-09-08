from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy import UniqueConstraint

from backend.db.base import Base


class DocumentLayoutModel(Base):
    __tablename__ = "document_layouts"
    __table_args__ = (UniqueConstraint("document_id", "page", name="uq_document_layouts_doc_page"),)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    page = Column(Integer, nullable=False)
    blocks = Column(JSONB, nullable=False, default=list)
    model = Column(String, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))