from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, BigInteger, DateTime, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from backend.db.base import Base


class DeliverableModel(Base):
    """A generated file artifact (Word/Excel/PowerPoint) written to the vault.

    Produced only after HITL approval, owned by the requesting user, linked to
    the session/turn that created it.
    """

    __tablename__ = "deliverables"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    session_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    turn_id = Column(PG_UUID(as_uuid=True), nullable=False)
    kind = Column(String, nullable=False)
    title = Column(Text, nullable=False, default="")
    filename = Column(Text, nullable=False)
    mime = Column(Text, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    storage_key = Column(Text, nullable=False)
    sha256 = Column(String, nullable=False)
    content_meta = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))