from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Integer, String, Text, DateTime, JSON, Float
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from backend.db.base import Base


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    turn_id = Column(PG_UUID(as_uuid=True), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False, default="")
    intent = Column(String, nullable=True)
    route_confidence = Column(Float, nullable=True)
    grounded = Column(Boolean, nullable=True)
    abstained = Column(Boolean, nullable=True)
    citations = Column(JSON, nullable=True)
    reasoning = Column(JSON, nullable=True)
    sources = Column(JSON, nullable=True)
    files = Column(JSON, nullable=True)
    tokens_in = Column(Integer, nullable=True)
    tokens_out = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
