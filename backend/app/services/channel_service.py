"""
Channel service: DB queries for channel observations.
"""
import pandas as pd
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset
from app.models.observation import ChannelObservation
from app.schemas.channel import ChannelInfo, HourlyPoint, MonthlyObservation, ObservationPoint


async def get_channel_list(db: AsyncSession) -> list[ChannelInfo]:
    """Return distinct channels with stats from all active datasets."""
    result = await db.execute(
        select(
            ChannelObservation.channel,
            func.count(ChannelObservation.id).label("row_count"),
            func.min(ChannelObservation.obs_date).label("date_min"),
            func.max(ChannelObservation.obs_date).label("date_max"),
            func.max(ChannelObservation.obs_hour).label("max_hour"),
            func.max(cast(Dataset.has_aht, Integer)).label("has_aht"),
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
            is_hourly=row.max_hour is not None,
            has_aht=bool(row.has_aht),
        )
        for row in rows
    ]


async def get_observations(db: AsyncSession, channel: str) -> list[ObservationPoint]:
    """Daily observations for a channel from active datasets (aggregated to day-level)."""
    result = await db.execute(
        select(
            ChannelObservation.obs_date,
            func.sum(ChannelObservation.volume).label("volume"),
        )
        .join(Dataset, Dataset.id == ChannelObservation.dataset_id)
        .where(Dataset.is_active == True)  # noqa: E712
        .where(ChannelObservation.channel == channel)
        .group_by(ChannelObservation.obs_date)
        .order_by(ChannelObservation.obs_date)
    )
    rows = result.all()
    return [ObservationPoint(date=row.obs_date, volume=float(row.volume)) for row in rows]


async def get_hourly_pattern(db: AsyncSession, channel: str) -> list[HourlyPoint]:
    """Average volume by hour-of-day (0–23) across all days in active datasets."""
    result = await db.execute(
        select(
            ChannelObservation.obs_hour,
            func.avg(ChannelObservation.volume).label("avg_volume"),
        )
        .join(Dataset, Dataset.id == ChannelObservation.dataset_id)
        .where(Dataset.is_active == True)  # noqa: E712
        .where(ChannelObservation.channel == channel)
        .where(ChannelObservation.obs_hour.isnot(None))
        .group_by(ChannelObservation.obs_hour)
        .order_by(ChannelObservation.obs_hour)
    )
    rows = result.all()
    return [HourlyPoint(hour=row.obs_hour, avg_volume=round(float(row.avg_volume), 2)) for row in rows]


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
