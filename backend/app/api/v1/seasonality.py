"""
Seasonality routes: GET /seasonality/{channel}
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.forecast import SeasonalityResponse
from app.services import forecasting_service

router = APIRouter()


@router.get("/{channel}", response_model=SeasonalityResponse)
async def get_seasonality(channel: str, db: AsyncSession = Depends(get_db)):
    """Return monthly factors and weekly day-of-week pattern for a channel."""
    result = await forecasting_service.get_seasonality(db, channel)
    if result is None:
        raise HTTPException(404, f"No trained model found for channel '{channel}'")
    return result
