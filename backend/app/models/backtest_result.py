import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    training_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("training_runs.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    holdout_days: Mapped[int] = mapped_column(Integer, nullable=False)
    mape: Mapped[float | None] = mapped_column(Numeric(8, 4))
    mae: Mapped[float | None] = mapped_column(Numeric(12, 4))
    rmse: Mapped[float | None] = mapped_column(Numeric(12, 4))
    # [{date, actual, predicted, error_pct}]
    data: Mapped[list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
