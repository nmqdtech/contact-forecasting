"""add hourly support (obs_hour + is_hourly)

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop the old unique constraint (dataset_id, channel, obs_date)
    op.drop_constraint("uq_obs", "channel_observations", type_="unique")

    # 2. Add obs_hour column (nullable)
    op.add_column(
        "channel_observations",
        sa.Column("obs_hour", sa.Integer, nullable=True),
    )

    # 3. Re-create unique constraint including obs_hour
    #    NULL == NULL in standard SQL causes issues, so we use a unique index with COALESCE
    op.execute(
        """
        CREATE UNIQUE INDEX uq_obs ON channel_observations
            (dataset_id, channel, obs_date, COALESCE(obs_hour, -1))
        """
    )

    # 4. Add is_hourly flag to datasets
    op.add_column(
        "datasets",
        sa.Column("is_hourly", sa.Boolean, nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("datasets", "is_hourly")
    op.execute("DROP INDEX IF EXISTS uq_obs")
    op.drop_column("channel_observations", "obs_hour")
    op.create_unique_constraint(
        "uq_obs", "channel_observations", ["dataset_id", "channel", "obs_date"]
    )
