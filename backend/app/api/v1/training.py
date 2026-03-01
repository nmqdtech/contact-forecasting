"""
Training routes: POST /training, GET /training/{job_id}
"""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.training import TrainingJobStatus, TrainingRequest
from app.services import forecasting_service

router = APIRouter()


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def start_training(
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Kick off a background training job for the requested channels."""
    job_id = await forecasting_service.start_training_job(db, background_tasks, request)
    return {"job_id": str(job_id), "status": "pending"}


@router.get("/{job_id}", response_model=TrainingJobStatus)
async def get_training_status(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Poll the status of a training job."""
    result = await forecasting_service.get_job_status(db, job_id)
    if result is None:
        raise HTTPException(404, "Training job not found")
    return result
