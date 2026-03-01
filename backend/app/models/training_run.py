import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TrainingRun(Base):
    __tablename__ = "training_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    months_ahead: Mapped[int] = mapped_column(Integer, default=15, nullable=False)

    # Model output (populated after training completes)
    model_config: Mapped[list | None] = mapped_column(JSONB)      # ["add","add",true]
    aic: Mapped[float | None] = mapped_column(Numeric(12, 4))
    monthly_factors: Mapped[dict | None] = mapped_column(JSONB)   # {"1":0.99,...}
    error_message: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Only the most-recent successful run per channel is active
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
