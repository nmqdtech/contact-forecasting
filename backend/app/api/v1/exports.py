"""
Export routes: GET /exports/forecasts, GET /exports/summary, GET /exports/iex
"""
import io
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.export_service import build_forecasts_excel, build_summary_excel
from app.core.forecasting_engine import ContactForecaster
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


@router.get("/report")
async def download_pdf_report(db: AsyncSession = Depends(get_db)):
    """Download a multi-page PDF report with forecasts and backtest charts."""
    pdf_bytes = await forecasting_service.generate_pdf_report(db)
    if not pdf_bytes:
        raise HTTPException(404, "No data available — train models first")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=forecast-report.pdf"},
    )


@router.get("/iex")
async def export_iex(
    channels: Annotated[list[str] | None, Query()] = None,
    min_aht: Annotated[float | None, Query(ge=1)] = None,
    max_aht: Annotated[float | None, Query(ge=1)] = None,
    db: AsyncSession = Depends(get_db),
):
    """Download a NICE IEX-formatted CSV with 30-min intervals.

    Columns: Skill, Date (MM/DD/YYYY), Start Time (HH:MM), Contacts (int), AHT (seconds × 100).
    Volume is split distributively using the channel's historical hourly pattern.
    AHT is linearly interpolated across 30-min slots between consecutive days.
    """
    if not channels:
        infos = await channel_service.get_channel_list(db)
        channels = [c.name for c in infos]

    all_rows: list[dict] = []

    for channel in channels:
        fc = await forecasting_service.get_forecast(db, channel)
        if not fc or not fc.data:
            continue

        # Build daily series
        vol_series = pd.Series(
            {p.date: float(p.yhat) for p in fc.data}
        )
        has_aht = any(p.aht_yhat is not None for p in fc.data)
        aht_series = pd.Series(
            {p.date: float(p.aht_yhat) if p.aht_yhat is not None else 0.0 for p in fc.data}
        ) if has_aht else pd.Series({p.date: 0.0 for p in fc.data})

        # Apply min/max AHT clamping
        if has_aht:
            if min_aht is not None:
                aht_series = aht_series.clip(lower=min_aht)
            if max_aht is not None:
                aht_series = aht_series.clip(upper=max_aht)

        # Get hourly distribution weights from historical pattern
        hourly_pts = await channel_service.get_hourly_pattern(db, channel)
        if hourly_pts:
            total_avg = sum(p.avg_volume for p in hourly_pts) or 1.0
            hourly_weights = {p.hour: p.avg_volume / total_avg for p in hourly_pts}
        else:
            hourly_weights = None  # uniform

        # Resample to 30-min slots
        slots_df = ContactForecaster.resample_to_30min(vol_series, aht_series, hourly_weights)

        for _, row in slots_df.iterrows():
            dt = row["ds"]
            aht_iex = round(row["aht_seconds"] * 100) if has_aht and row["aht_seconds"] > 0 else 0
            all_rows.append({
                "Skill": channel,
                "Date": dt.strftime("%m/%d/%Y"),
                "Start Time": dt.strftime("%H:%M"),
                "Contacts": int(row["contacts"]),
                "AHT": aht_iex,
            })

    if not all_rows:
        raise HTTPException(404, "No forecast data available — train models first")

    df_out = pd.DataFrame(all_rows, columns=["Skill", "Date", "Start Time", "Contacts", "AHT"])
    csv_buf = io.StringIO()
    df_out.to_csv(csv_buf, index=False)
    csv_bytes = csv_buf.getvalue().encode("utf-8")

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=iex-forecast.csv"},
    )
