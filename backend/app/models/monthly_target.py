import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class MonthlyTarget(Base):
    __tablename__ = "monthly_targets"
    __table_args__ = (UniqueConstraint("channel", "month", name="uq_target"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    month: Mapped[str] = mapped_column(String(7), nullable=False)  # 'YYYY-MM'
    volume: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
