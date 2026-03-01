"""
Upload routes: POST /uploads, GET /uploads, DELETE /uploads/{id}
"""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.data_processor import DataValidationError, extract_metadata, parse_excel
from app.db.database import get_db
from app.models.dataset import Dataset
from app.models.observation import ChannelObservation
from app.schemas.upload import DatasetOut, DatasetSummary

router = APIRouter()


@router.post("", response_model=DatasetOut, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Parse an Excel file, persist observations, and activate the dataset."""
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(422, "Only .xlsx / .xls files are supported")

    content = await file.read()

    try:
        df = parse_excel(content)
    except DataValidationError as exc:
        raise HTTPException(422, str(exc)) from exc

    meta = extract_metadata(df)

    # Deactivate all previous datasets
    await db.execute(update(Dataset).values(is_active=False))

    # Create new dataset record
    dataset = Dataset(
        filename=file.filename,
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
            for _, row in df.iterrows()
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


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_dataset(dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Soft-delete (deactivate) a dataset."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(404, "Dataset not found")
    dataset.is_active = False
    await db.commit()
