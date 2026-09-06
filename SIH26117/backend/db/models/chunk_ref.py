from __future__ import annotations

import uuid

from sqlalchemy import Column, Integer, SmallInteger, String, Text, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from backend.db.base import Base


class ChunkRefModel(Base):
    __tablename__ = "chunk_refs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_type = Column(String, nullable=False)
    page_start = Column(Integer, nullable=False)
    page_end = Column(Integer, nullable=False)
    bbox = Column(JSON, nullable=True)
    heading_path = Column(JSON, nullable=True)
    token_count = Column(Integer, nullable=False, default=0)
    text_preview = Column(Text, nullable=False, default="")
    suspected_injection = Column(Boolean, nullable=False, default=False)
