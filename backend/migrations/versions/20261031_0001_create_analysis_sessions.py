"""create analysis_sessions

Revision ID: 0001
Revises:
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("verdict", sa.String(length=16), nullable=False),
        sa.Column("recommended_action", sa.String(length=32), nullable=False),
        sa.Column("client_request_id", sa.String(length=100), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("score BETWEEN 0 AND 10", name="ck_analysis_score"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analysis_sessions_client_request_id", "analysis_sessions", ["client_request_id"]
    )
    op.create_index("ix_analysis_sessions_created_at", "analysis_sessions", ["created_at"])
    op.create_index("ix_analysis_sessions_expires_at", "analysis_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_analysis_sessions_expires_at", table_name="analysis_sessions")
    op.drop_index("ix_analysis_sessions_created_at", table_name="analysis_sessions")
    op.drop_index("ix_analysis_sessions_client_request_id", table_name="analysis_sessions")
    op.drop_table("analysis_sessions")
