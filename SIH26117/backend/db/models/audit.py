from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, Integer, JSON, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, INET

from backend.db.base import Base


class AuditLogModel(Base):
    __tablename__ = "audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user_id = Column(PG_UUID(as_uuid=True), nullable=True)
    role = Column(String, nullable=True)
    clearance_at_time = Column(SmallInteger, nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    route = Column(String, nullable=True)
    intent = Column(String, nullable=True)
    tool_calls = Column(JSON, nullable=True)
    document_ids = Column(JSON, nullable=True)
    prompt_hash = Column(String, nullable=True)
    decision = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    ip = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    correlation_id = Column(String, nullable=True)
    prev_hash = Column(Text, nullable=False)
    entry_hash = Column(Text, nullable=False, unique=True)


class AuditChainHead(Base):
    __tablename__ = "audit_chain_head"

    id = Column(Integer, primary_key=True, default=1)
    last_hash = Column(Text, nullable=False, default="genesis")
