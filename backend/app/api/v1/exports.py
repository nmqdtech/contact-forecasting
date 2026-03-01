"""
Export routes: GET /exports/forecasts, GET /exports/summary
"""
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.export_service import build_forecasts_excel, build_summary_excel
from app.db.database import get_db
from app.services import channel_service, forecasting_service

router = APIRouter()

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/forecasts")
async def export_forecasts(
    channels: Annotated[list[str] | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
):
    """Download an Excel workbook with one sheet per channel (daily forecasts)."""
    if not channels:
        infos = await channel_service.get_channel_list(db)
        channels = [c.name for c in infos]

    channel_forecasts: dict[str, pd.DataFrame] = {}
    for channel in channels:
        fc = await forecasting_service.get_forecast(db, channel)
        if fc:
            channel_forecasts[channel] = pd.DataFrame(
                [
                    {
                        "date": p.date,
                        "yhat": p.yhat,
                        "yhat_lower": p.yhat_lower,
                        "yhat_upper": p.yhat_upper,
                    }
                    for p in fc.data
                ]
            )

    if not channel_forecasts:
        raise HTTPException(404, "No forecast data available — train models first")

    excel_bytes = build_forecasts_excel(channel_forecasts)
    return Response(
        content=excel_bytes,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": "attachment; filename=forecasts.xlsx"},
    )


@router.get("/summary")
async def export_summary(db: AsyncSession = Depends(get_db)):
    """Download an Excel workbook with the cross-channel summary."""
    rows = await forecasting_service.get_summary_rows(db)
    if not rows:
        raise HTTPException(404, "No summary data available — train models first")

    excel_bytes = build_summary_excel([row.model_dump() for row in rows])
    return Response(
        content=excel_bytes,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": "attachment; filename=summary.xlsx"},
    )
