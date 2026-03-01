import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TrainingRequest(BaseModel):
    dataset_id: uuid.UUID
    channels: list[str] = Field(min_length=1)
    months_ahead: int = Field(default=15, ge=1, le=24)


class ChannelTrainingResult(BaseModel):
    channel: str
    status: str          # pending | running | completed | failed
    config: list | None = None       # ["add","add",true]
    aic: float | None = None
    backtest_mape: float | None = None
    message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TrainingJobStatus(BaseModel):
    job_id: uuid.UUID
    status: str          # pending | running | completed | failed
    progress: float      # 0.0 – 1.0
    results: list[ChannelTrainingResult]
