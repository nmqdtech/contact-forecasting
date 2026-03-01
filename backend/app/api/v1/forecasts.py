"""
Forecast routes: GET /forecasts/{channel}, /monthly, /backtest
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.forecast import BacktestResponse, ForecastResponse, MonthlyForecastResponse
from app.services import forecasting_service

router = APIRouter()


@router.get("/{channel}", response_model=ForecastResponse)
async def get_forecast(channel: str, db: AsyncSession = Depends(get_db)):
    """Return daily forecast for a channel (from its active training run)."""
    result = await forecasting_service.get_forecast(db, channel)
    if result is None:
        raise HTTPException(404, f"No active forecast for channel '{channel}'")
    return result


@router.get("/{channel}/monthly", response_model=MonthlyForecastResponse)
async def get_monthly_forecast(channel: str, db: AsyncSession = Depends(get_db)):
    """Return historical monthly totals and monthly forecast aggregates."""
    result = await forecasting_service.get_monthly_forecast(db, channel)
    if result is None:
        raise HTTPException(404, f"No active forecast for channel '{channel}'")
    return result


@router.get("/{channel}/backtest", response_model=BacktestResponse)
async def get_backtest(channel: str, db: AsyncSession = Depends(get_db)):
    """Return backtest results for a channel."""
    result = await forecasting_service.get_backtest(db, channel)
    if result is None:
        raise HTTPException(404, f"No backtest results for channel '{channel}'")
    return result
