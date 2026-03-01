import uuid
from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Forecast(Base):
    __tablename__ = "forecasts"
    __table_args__ = (
        UniqueConstraint("training_run_id", "channel", "forecast_date", name="uq_forecast"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    training_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("training_runs.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False)
    yhat: Mapped[float | None] = mapped_column(Numeric(12, 2))
    yhat_lower: Mapped[float | None] = mapped_column(Numeric(12, 2))
    yhat_upper: Mapped[float | None] = mapped_column(Numeric(12, 2))
