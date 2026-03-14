"""
Channel routes: GET /channels, GET /channels/{channel}/data, /monthly, /hourly
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.channel import ChannelInfo, HourlyPoint, MonthlyObservation, ObservationPoint
from app.services import channel_service

router = APIRouter()


@router.get("", response_model=list[ChannelInfo])
async def list_channels(
    project_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Return distinct channels for active datasets (optionally scoped to a project)."""
    return await channel_service.get_channel_list(db, project_id=project_id)


@router.get("/{channel}/data", response_model=list[ObservationPoint])
async def get_channel_data(
    channel: str,
    project_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Return daily observations for a channel."""
    obs = await channel_service.get_observations(db, channel, project_id=project_id)
    if not obs:
        raise HTTPException(404, f"No data found for channel '{channel}'")
    return obs


@router.get("/{channel}/monthly", response_model=list[MonthlyObservation])
async def get_channel_monthly(
    channel: str,
    project_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Return monthly aggregated observations for a channel."""
    monthly = await channel_service.get_monthly_historical(
        db, channel, project_id=project_id
    )
    if not monthly:
        raise HTTPException(404, f"No data found for channel '{channel}'")
    return monthly


@router.get("/{channel}/hourly", response_model=list[HourlyPoint])
async def get_channel_hourly(
    channel: str,
    project_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Return average volume by hour-of-day (only for hourly datasets)."""
    pattern = await channel_service.get_hourly_pattern(
        db, channel, project_id=project_id
    )
    if not pattern:
        raise HTTPException(404, f"No hourly data found for channel '{channel}'")
    return pattern
