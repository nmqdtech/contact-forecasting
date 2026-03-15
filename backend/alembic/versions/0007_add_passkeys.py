"""add passkeys table

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: str = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "passkeys",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("credential_id", sa.LargeBinary, unique=True, nullable=False),
        sa.Column("public_key", sa.LargeBinary, nullable=False),
        sa.Column("sign_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("name", sa.String(100), nullable=False, server_default="Passkey"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("passkeys")
