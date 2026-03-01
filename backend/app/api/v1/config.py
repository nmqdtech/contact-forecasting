"""
Config routes: GET /config, PUT/DELETE /config/holidays, PUT/DELETE /config/targets
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.config import ConfigResponse, HolidayConfigRequest, MonthlyTargetsRequest
from app.services import config_service

router = APIRouter()


@router.get("", response_model=ConfigResponse)
async def get_config(db: AsyncSession = Depends(get_db)):
    """Return all holiday configs and monthly targets."""
    return await config_service.get_all_configs(db)


@router.put("/holidays", status_code=status.HTTP_204_NO_CONTENT)
async def set_holiday(req: HolidayConfigRequest, db: AsyncSession = Depends(get_db)):
    """Set the holiday country code for a channel."""
    await config_service.upsert_holiday(db, req.channel, req.country_code)


@router.delete("/holidays/{channel}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holiday(channel: str, db: AsyncSession = Depends(get_db)):
    """Remove the holiday config for a channel."""
    deleted = await config_service.delete_holiday(db, channel)
    if not deleted:
        raise HTTPException(404, f"No holiday config found for channel '{channel}'")


@router.put("/targets", status_code=status.HTTP_204_NO_CONTENT)
async def set_targets(req: MonthlyTargetsRequest, db: AsyncSession = Depends(get_db)):
    """Upsert monthly volume targets for a channel."""
    await config_service.upsert_targets(db, req.channel, req.targets)


@router.delete("/targets/{channel}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_targets(channel: str, db: AsyncSession = Depends(get_db)):
    """Remove all monthly targets for a channel."""
    deleted = await config_service.delete_targets(db, channel)
    if not deleted:
        raise HTTPException(404, f"No targets found for channel '{channel}'")
