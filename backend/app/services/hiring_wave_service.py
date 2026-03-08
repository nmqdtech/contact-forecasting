"""CRUD operations for hiring waves."""
import uuid
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hiring_wave import HiringWave


async def list_waves(db: AsyncSession, channel: str) -> list[HiringWave]:
    result = await db.execute(
        select(HiringWave)
        .where(HiringWave.channel == channel)
        .order_by(HiringWave.start_date)
    )
    return list(result.scalars().all())


async def list_all_waves(db: AsyncSession) -> list[HiringWave]:
    result = await db.execute(select(HiringWave).order_by(HiringWave.channel, HiringWave.start_date))
    return list(result.scalars().all())


async def create_wave(
    db: AsyncSession,
    channel: str,
    start_date: date,
    end_date: date,
    junior_count: int,
    total_agents: int,
    label: str | None = None,
) -> HiringWave:
    wave = HiringWave(
        channel=channel,
        start_date=start_date,
        end_date=end_date,
        junior_count=junior_count,
        total_agents=total_agents,
        label=label,
    )
    db.add(wave)
    await db.commit()
    await db.refresh(wave)
    return wave


async def delete_wave(db: AsyncSession, wave_id: uuid.UUID) -> bool:
    result = await db.execute(select(HiringWave).where(HiringWave.id == wave_id))
    wave = result.scalar_one_or_none()
    if wave is None:
        return False
    await db.execute(delete(HiringWave).where(HiringWave.id == wave_id))
    await db.commit()
    return True


def build_future_junior_ratios(waves: list[HiringWave], forecast_dates) -> dict[str, float]:
    """Build {date_str: junior_ratio} mapping for forecast period from hiring waves."""
    ratios: dict[str, float] = {}
    for dt in forecast_dates:
        d = dt.date() if hasattr(dt, "date") else dt
        for wave in waves:
            if wave.start_date <= d <= wave.end_date:
                ratios[str(d)] = wave.junior_ratio
                break  # first matching wave wins (they should not overlap, but safety first)
    return ratios
