"""
Summary route: GET /summary
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.config import SummaryRow
from app.services import forecasting_service

router = APIRouter()


@router.get("", response_model=list[SummaryRow])
async def get_summary(db: AsyncSession = Depends(get_db)):
    """Return a cross-channel summary of historical vs. forecast metrics."""
    return await forecasting_service.get_summary_rows(db)
