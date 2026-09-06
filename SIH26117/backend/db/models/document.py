from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, Column, Integer, SmallInteger, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from backend.db.base import Base


class DocumentModel(Base):
    __tablename__ = "documents"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    filename = Column(Text, nullable=False)
    mime = Column(Text, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    page_count = Column(Integer, nullable=False, default=0)
    checksum = Column(Text, unique=True, nullable=False, index=True)
    storage_key = Column(Text, nullable=False)
    wrapped_dek = Column(Text, nullable=False, default="")
    clearance_level = Column(SmallInteger, nullable=False, default=0)
    department = Column(String, nullable=False, default="ADMIN")
    legal_hold = Column(Boolean, nullable=False, default=False)
    status = Column(String, nullable=False, default="QUEUED", index=True)
    error_reason = Column(Text, nullable=True)
    chunk_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ingested_at = Column(DateTime(timezone=True), nullable=True)
