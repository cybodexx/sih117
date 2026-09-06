from __future__ import annotations

from pydantic import BaseModel


class DocumentAccepted(BaseModel):
    document_id: str
    status: str = "QUEUED"
    checksum: str
    deduplicated: bool = False


class DocumentRead(BaseModel):
    id: str
    filename: str
    mime: str
    size_bytes: int
    page_count: int
    status: str
    chunk_count: int
    clearance_level: int
    department: str
    owner_id: str
    checksum: str
    error_reason: str | None = None
    created_at: str
    ingested_at: str | None = None


class DocumentLabelUpdate(BaseModel):
    clearance_level: int
    department: str


class PageRead(BaseModel):
    items: list[DocumentRead]
    total: int
    page: int
    size: int
