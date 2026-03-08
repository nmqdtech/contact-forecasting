"""add AHT, junior_ratio, hiring_waves

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # channel_observations: optional AHT + junior ratio per row
    op.add_column("channel_observations", sa.Column("aht", sa.Numeric(10, 4), nullable=True))
    op.add_column("channel_observations", sa.Column("junior_ratio", sa.Numeric(5, 4), nullable=True))

    # datasets: flag for AHT presence
    op.add_column(
        "datasets",
        sa.Column("has_aht", sa.Boolean(), nullable=False, server_default="false"),
    )

    # forecasts: AHT point forecast (seconds)
    op.add_column("forecasts", sa.Column("aht_yhat", sa.Numeric(10, 4), nullable=True))

    # Hiring waves table
    op.create_table(
        "hiring_waves",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("channel", sa.String(100), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("junior_count", sa.Integer(), nullable=False),
        sa.Column("total_agents", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_hiring_waves_channel", "hiring_waves", ["channel"])


def downgrade() -> None:
    op.drop_index("ix_hiring_waves_channel", "hiring_waves")
    op.drop_table("hiring_waves")
    op.drop_column("forecasts", "aht_yhat")
    op.drop_column("datasets", "has_aht")
    op.drop_column("channel_observations", "junior_ratio")
    op.drop_column("channel_observations", "aht")
