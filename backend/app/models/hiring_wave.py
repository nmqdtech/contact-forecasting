import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class HiringWave(Base):
    __tablename__ = "hiring_waves"
    __table_args__ = (Index("ix_hiring_waves_channel", "channel"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    junior_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_agents: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    @property
    def junior_ratio(self) -> float:
        if self.total_agents <= 0:
            return 0.0
        return min(1.0, self.junior_count / self.total_agents)
