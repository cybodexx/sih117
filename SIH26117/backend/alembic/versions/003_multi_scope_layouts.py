"""Multi-file chat scope + document layout table.

Revision ID: 003_multi_scope_layouts
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_multi_scope_layouts"
down_revision: Union[str, None] = "002_deliverables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS document_ids JSONB"
    )
    op.create_table(
        "document_layouts",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("blocks", sa.dialects.postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("model", sa.String(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("document_id", "page", name="uq_document_layouts_doc_page"),
    )


def downgrade() -> None:
    op.drop_table("document_layouts")
    op.execute("ALTER TABLE chat_sessions DROP COLUMN IF EXISTS document_ids")