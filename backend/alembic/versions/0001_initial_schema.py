"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── datasets ──────────────────────────────────────────────────────────────
    op.create_table(
        "datasets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("upload_ts", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("row_count", sa.Integer),
        sa.Column("date_min", sa.Date),
        sa.Column("date_max", sa.Date),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )

    # ── channel_observations ──────────────────────────────────────────────────
    op.create_table(
        "channel_observations",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("dataset_id", UUID(as_uuid=True),
                  sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(100), nullable=False),
        sa.Column("obs_date", sa.Date, nullable=False),
        sa.Column("volume", sa.Numeric(12, 2), nullable=False),
        sa.UniqueConstraint("dataset_id", "channel", "obs_date", name="uq_obs"),
    )
    op.create_index("idx_obs_channel_date", "channel_observations",
                    ["channel", "obs_date"])

    # ── channel_configs ───────────────────────────────────────────────────────
    op.create_table(
        "channel_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("channel", sa.String(100), nullable=False, unique=True),
        sa.Column("country_code", sa.String(10)),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )

    # ── monthly_targets ───────────────────────────────────────────────────────
    op.create_table(
        "monthly_targets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("channel", sa.String(100), nullable=False),
        sa.Column("month", sa.String(7), nullable=False),
        sa.Column("volume", sa.Numeric(14, 2), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.UniqueConstraint("channel", "month", name="uq_target"),
    )

    # ── training_runs ─────────────────────────────────────────────────────────
    op.create_table(
        "training_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(100), nullable=False),
        sa.Column("dataset_id", UUID(as_uuid=True),
                  sa.ForeignKey("datasets.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("months_ahead", sa.Integer, nullable=False, server_default="15"),
        sa.Column("model_config", JSONB),
        sa.Column("aic", sa.Numeric(12, 4)),
        sa.Column("monthly_factors", JSONB),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("idx_training_job_id", "training_runs", ["job_id"])
    op.create_index("idx_training_channel_active", "training_runs",
                    ["channel", "is_active"])

    # ── forecasts ─────────────────────────────────────────────────────────────
    op.create_table(
        "forecasts",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("training_run_id", UUID(as_uuid=True),
                  sa.ForeignKey("training_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(100), nullable=False),
        sa.Column("forecast_date", sa.Date, nullable=False),
        sa.Column("yhat", sa.Numeric(12, 2)),
        sa.Column("yhat_lower", sa.Numeric(12, 2)),
        sa.Column("yhat_upper", sa.Numeric(12, 2)),
        sa.UniqueConstraint("training_run_id", "channel", "forecast_date",
                            name="uq_forecast"),
    )
    op.create_index("idx_forecasts_channel_date", "forecasts",
                    ["channel", "forecast_date"])

    # ── backtest_results ──────────────────────────────────────────────────────
    op.create_table(
        "backtest_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("training_run_id", UUID(as_uuid=True),
                  sa.ForeignKey("training_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(100), nullable=False),
        sa.Column("holdout_days", sa.Integer, nullable=False),
        sa.Column("mape", sa.Numeric(8, 4)),
        sa.Column("mae", sa.Numeric(12, 4)),
        sa.Column("rmse", sa.Numeric(12, 4)),
        sa.Column("data", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("backtest_results")
    op.drop_index("idx_forecasts_channel_date", "forecasts")
    op.drop_table("forecasts")
    op.drop_index("idx_training_channel_active", "training_runs")
    op.drop_index("idx_training_job_id", "training_runs")
    op.drop_table("training_runs")
    op.drop_table("monthly_targets")
    op.drop_table("channel_configs")
    op.drop_index("idx_obs_channel_date", "channel_observations")
    op.drop_table("channel_observations")
    op.drop_table("datasets")
