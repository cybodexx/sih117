from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from backend.db.base import Base


class ApprovalModel(Base):
    __tablename__ = "approvals"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    turn_id = Column(PG_UUID(as_uuid=True), nullable=False)
    tool = Column(String, nullable=False)
    risk = Column(String, nullable=False)
    arguments = Column(JSON, nullable=True)
    decision = Column(String, nullable=True)
    decided_by = Column(PG_UUID(as_uuid=True), nullable=True)
    note = Column(Text, nullable=True)
    requested_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    decided_at = Column(DateTime(timezone=True), nullable=True)
