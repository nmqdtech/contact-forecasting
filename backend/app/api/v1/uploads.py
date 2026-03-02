"""
Upload routes: POST /uploads, GET /uploads, DELETE /uploads/reset, DELETE /uploads/{id}
"""
import uuid

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.data_processor import DataValidationError, extract_metadata, parse_excel
from app.db.database import get_db
from app.models.backtest_result import BacktestResult
from app.models.channel_config import ChannelConfig
from app.models.dataset import Dataset
from app.models.forecast import Forecast
from app.models.monthly_target import MonthlyTarget
from app.models.observation import ChannelObservation
from app.models.training_run import TrainingRun
from app.schemas.upload import DatasetOut, DatasetSummary

router = APIRouter()


@router.post("", response_model=DatasetOut, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Parse one or more Excel files, merge them, persist observations, and activate the dataset."""
    if not files:
        raise HTTPException(422, "At least one file is required")

    frames: list[pd.DataFrame] = []
    filenames: list[str] = []

    for file in files:
        if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
            raise HTTPException(422, f"{file.filename!r}: only .xlsx / .xls files are supported")
        content = await file.read()
        try:
            df = parse_excel(content)
        except DataValidationError as exc:
            raise HTTPException(422, f"{file.filename}: {exc}") from exc
        frames.append(df)
        filenames.append(file.filename)

    # Merge: sum volume for same (Channel, Date) across files
    if len(frames) == 1:
        merged = frames[0]
    else:
        raw = pd.concat(frames, ignore_index=True)
        merged = (
            raw.groupby(["Channel", "Date"], as_index=False)["Volume"]
            .sum()
            .sort_values("Date")
        )

    combined_filename = " + ".join(filenames) if len(filenames) > 1 else filenames[0]
    meta = extract_metadata(merged)

    # Deactivate all previous datasets
    await db.execute(update(Dataset).values(is_active=False))

    # Create new dataset record
    dataset = Dataset(
        filename=combined_filename,
        row_count=meta["row_count"],
        date_min=meta["date_min"],
        date_max=meta["date_max"],
        is_active=True,
    )
    db.add(dataset)
    await db.flush()  # populate dataset.id

    # Insert observations
    db.add_all(
        [
            ChannelObservation(
                dataset_id=dataset.id,
                channel=str(row["Channel"]),
                obs_date=row["Date"].date(),
                volume=float(row["Volume"]),
            )
            for _, row in merged.iterrows()
        ]
    )
    await db.commit()
    await db.refresh(dataset)

    return DatasetOut(
        dataset_id=dataset.id,
        filename=dataset.filename,
        upload_ts=dataset.upload_ts,
        row_count=dataset.row_count,
        channels=meta["channels"],
        date_min=dataset.date_min,
        date_max=dataset.date_max,
    )


@router.get("", response_model=list[DatasetSummary])
async def list_datasets(db: AsyncSession = Depends(get_db)):
    """List all uploaded datasets, most recent first."""
    result = await db.execute(select(Dataset).order_by(Dataset.upload_ts.desc()))
    return [
        DatasetSummary(
            dataset_id=d.id,
            filename=d.filename,
            upload_ts=d.upload_ts,
            row_count=d.row_count or 0,
            is_active=d.is_active,
        )
        for d in result.scalars().all()
    ]


@router.delete("/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_all_data(db: AsyncSession = Depends(get_db)):
    """Hard-delete all data: forecasts, backtest results, training runs, observations, datasets, configs."""
    # Delete in dependency order (children before parents)
    await db.execute(delete(BacktestResult))
    await db.execute(delete(Forecast))
    await db.execute(delete(TrainingRun))
    await db.execute(delete(ChannelObservation))
    await db.execute(delete(Dataset))
    await db.execute(delete(ChannelConfig))
    await db.execute(delete(MonthlyTarget))
    await db.commit()


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_dataset(dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Soft-delete (deactivate) a dataset."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(404, "Dataset not found")
    dataset.is_active = False
    await db.commit()
