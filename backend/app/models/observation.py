import uuid
from datetime import date
from typing import Optional

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ChannelObservation(Base):
    __tablename__ = "channel_observations"
    __table_args__ = (
        # Use a partial-index-compatible constraint: treat NULL hour as -1 sentinel
        # handled in migration via expression index; here we just name it
        UniqueConstraint("dataset_id", "channel", "obs_date", "obs_hour", name="uq_obs"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    obs_date: Mapped[date] = mapped_column(Date, nullable=False)
    obs_hour: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    volume: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
