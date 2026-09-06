from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Integer, SmallInteger, String, Text, ARRAY, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, INET

from backend.db.base import Base


class UserModel(Base):
    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(Text, nullable=False, default="")
    password_hash = Column(Text, nullable=False)
    role = Column(String, nullable=False, default="VIEWER")
    clearance_level = Column(SmallInteger, nullable=False, default=0)
    departments = Column(ARRAY(Text), nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True)
    failed_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
