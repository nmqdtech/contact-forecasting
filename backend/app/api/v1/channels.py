"""
Channel routes: GET /channels, GET /channels/{channel}/data, /monthly
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.channel import ChannelInfo, MonthlyObservation, ObservationPoint
from app.services import channel_service

router = APIRouter()


@router.get("", response_model=list[ChannelInfo])
async def list_channels(db: AsyncSession = Depends(get_db)):
    """Return distinct channels present in active datasets."""
    return await channel_service.get_channel_list(db)


@router.get("/{channel}/data", response_model=list[ObservationPoint])
async def get_channel_data(channel: str, db: AsyncSession = Depends(get_db)):
    """Return daily observations for a channel."""
    obs = await channel_service.get_observations(db, channel)
    if not obs:
        raise HTTPException(404, f"No data found for channel '{channel}'")
    return obs


@router.get("/{channel}/monthly", response_model=list[MonthlyObservation])
async def get_channel_monthly(channel: str, db: AsyncSession = Depends(get_db)):
    """Return monthly aggregated observations for a channel."""
    monthly = await channel_service.get_monthly_historical(db, channel)
    if not monthly:
        raise HTTPException(404, f"No data found for channel '{channel}'")
    return monthly
