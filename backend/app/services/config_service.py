"""
Config service: manage holiday configs and monthly targets.
"""
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel_config import ChannelConfig
from app.models.monthly_target import MonthlyTarget
from app.schemas.config import ConfigResponse


async def get_all_configs(db: AsyncSession) -> ConfigResponse:
    """Return all holiday configs and monthly targets."""
    hol_result = await db.execute(select(ChannelConfig))
    holidays = {
        c.channel: c.country_code
        for c in hol_result.scalars().all()
        if c.country_code
    }

    tgt_result = await db.execute(select(MonthlyTarget))
    targets: dict[str, dict[str, float]] = {}
    for t in tgt_result.scalars().all():
        targets.setdefault(t.channel, {})[t.month] = float(t.volume)

    return ConfigResponse(holidays=holidays, targets=targets)


async def upsert_holiday(db: AsyncSession, channel: str, country_code: str) -> None:
    """Set (or update) holiday config for a channel."""
    result = await db.execute(select(ChannelConfig).where(ChannelConfig.channel == channel))
    existing = result.scalar_one_or_none()
    if existing:
        existing.country_code = country_code
    else:
        db.add(ChannelConfig(channel=channel, country_code=country_code))
    await db.commit()


async def delete_holiday(db: AsyncSession, channel: str) -> bool:
    """Remove holiday config for a channel. Returns True if a row was deleted."""
    result = await db.execute(
        delete(ChannelConfig).where(ChannelConfig.channel == channel)
    )
    await db.commit()
    return result.rowcount > 0


async def upsert_targets(db: AsyncSession, channel: str, targets: dict[str, float]) -> None:
    """Upsert monthly targets for a channel."""
    for month, volume in targets.items():
        result = await db.execute(
            select(MonthlyTarget)
            .where(MonthlyTarget.channel == channel)
            .where(MonthlyTarget.month == month)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.volume = volume
        else:
            db.add(MonthlyTarget(channel=channel, month=month, volume=volume))
    await db.commit()


async def delete_targets(db: AsyncSession, channel: str) -> bool:
    """Remove all monthly targets for a channel. Returns True if any deleted."""
    result = await db.execute(
        delete(MonthlyTarget).where(MonthlyTarget.channel == channel)
    )
    await db.commit()
    return result.rowcount > 0
