"""
Channel service: DB queries for channel observations.
"""
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset
from app.models.observation import ChannelObservation
from app.schemas.channel import ChannelInfo, MonthlyObservation, ObservationPoint


async def get_channel_list(db: AsyncSession) -> list[ChannelInfo]:
    """Return distinct channels with stats from all active datasets."""
    result = await db.execute(
        select(
            ChannelObservation.channel,
            func.count(ChannelObservation.id).label("row_count"),
            func.min(ChannelObservation.obs_date).label("date_min"),
            func.max(ChannelObservation.obs_date).label("date_max"),
        )
        .join(Dataset, Dataset.id == ChannelObservation.dataset_id)
        .where(Dataset.is_active == True)  # noqa: E712
        .group_by(ChannelObservation.channel)
        .order_by(ChannelObservation.channel)
    )
    rows = result.all()
    return [
        ChannelInfo(
            name=row.channel,
            row_count=row.row_count,
            date_min=row.date_min,
            date_max=row.date_max,
        )
        for row in rows
    ]


async def get_observations(db: AsyncSession, channel: str) -> list[ObservationPoint]:
    """Daily observations for a channel from active datasets."""
    result = await db.execute(
        select(ChannelObservation.obs_date, ChannelObservation.volume)
        .join(Dataset, Dataset.id == ChannelObservation.dataset_id)
        .where(Dataset.is_active == True)  # noqa: E712
        .where(ChannelObservation.channel == channel)
        .order_by(ChannelObservation.obs_date)
    )
    rows = result.all()
    return [ObservationPoint(date=row.obs_date, volume=float(row.volume)) for row in rows]


async def get_monthly_historical(db: AsyncSession, channel: str) -> list[MonthlyObservation]:
    """Aggregate daily observations to monthly totals."""
    obs = await get_observations(db, channel)
    if not obs:
        return []
    df = pd.DataFrame([{"month": o.date.strftime("%Y-%m"), "volume": o.volume} for o in obs])
    monthly = df.groupby("month")["volume"].sum().reset_index()
    return [
        MonthlyObservation(month=row["month"], total=row["volume"])
        for _, row in monthly.iterrows()
    ]
