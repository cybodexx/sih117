from __future__ import annotations

from pydantic import BaseModel


class AttachmentAccepted(BaseModel):
    attachment_id: str
    name: str
    size: int
    mime: str