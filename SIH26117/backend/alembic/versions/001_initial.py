"""Initial schema — all tables from 04_INTEGRATION_CONTRACTS.md §4.

Revision ID: 001_initial
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.create_table(
        "users",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(), unique=True, nullable=False, index=True),
        sa.Column("full_name", sa.Text(), nullable=False, server_default=""),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="VIEWER"),
        sa.Column("clearance_level", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("departments", sa.dialects.postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("mime", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checksum", sa.Text(), unique=True, nullable=False, index=True),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("wrapped_dek", sa.Text(), nullable=False, server_default=""),
        sa.Column("clearance_level", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("department", sa.String(), nullable=False, server_default="ADMIN"),
        sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", sa.String(), nullable=False, server_default="QUEUED", index=True),
        sa.Column("error_reason", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_documents_status_dept", "documents", ["department", "clearance_level"])

    op.create_table(
        "chunk_refs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_type", sa.String(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("bbox", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("heading_path", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("text_preview", sa.Text(), nullable=False, server_default=""),
        sa.Column("suspected_injection", sa.Boolean(), nullable=False, server_default="false"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_chunk_doc_index"),
    )

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("title", sa.Text(), nullable=False, server_default="New Chat"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("turn_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("intent", sa.String(), nullable=True),
        sa.Column("route_confidence", sa.Float(), nullable=True),
        sa.Column("grounded", sa.Boolean(), nullable=True),
        sa.Column("abstained", sa.Boolean(), nullable=True),
        sa.Column("citations", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("reasoning", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("sources", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "approvals",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("turn_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tool", sa.String(), nullable=False),
        sa.Column("risk", sa.String(), nullable=False),
        sa.Column("arguments", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("decision", sa.String(), nullable=True),
        sa.Column("decided_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("clearance_at_time", sa.SmallInteger(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=True),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("route", sa.String(), nullable=True),
        sa.Column("intent", sa.String(), nullable=True),
        sa.Column("tool_calls", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("document_ids", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("prompt_hash", sa.String(), nullable=True),
        sa.Column("decision", sa.String(), nullable=True),
        sa.Column("severity", sa.String(), nullable=True),
        sa.Column("ip", sa.dialects.postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(), nullable=True),
        sa.Column("prev_hash", sa.Text(), nullable=False),
        sa.Column("entry_hash", sa.Text(), nullable=False, unique=True),
    )

    op.execute(
        "CREATE RULE audit_no_update AS ON UPDATE TO audit_log DO INSTEAD NOTHING"
    )
    op.execute(
        "CREATE RULE audit_no_delete AS ON DELETE TO audit_log DO INSTEAD NOTHING"
    )

    op.create_table(
        "audit_chain_head",
        sa.Column("id", sa.Integer(), sa.CheckConstraint("id = 1"), primary_key=True),
        sa.Column("last_hash", sa.Text(), nullable=False, server_default="genesis"),
    )
    op.execute(
        "INSERT INTO audit_chain_head (id, last_hash) VALUES (1, 'genesis') ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("audit_chain_head")
    op.drop_table("audit_log")
    op.drop_table("approvals")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("chunk_refs")
    op.drop_table("documents")
    op.drop_table("users")
