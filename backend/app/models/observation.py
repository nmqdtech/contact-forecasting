import uuid
from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ChannelObservation(Base):
    __tablename__ = "channel_observations"
    __table_args__ = (
        UniqueConstraint("dataset_id", "channel", "obs_date", name="uq_obs"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    obs_date: Mapped[date] = mapped_column(Date, nullable=False)
    volume: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
