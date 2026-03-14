import uuid
from datetime import date, datetime

from pydantic import BaseModel


class DatasetOut(BaseModel):
    dataset_id: uuid.UUID
    filename: str
    upload_ts: datetime
    row_count: int
    channels: list[str]
    date_min: date
    date_max: date
    is_hourly: bool = False
    has_aht: bool = False
    project_id: str | None = None
    is_actuals: bool = False

    model_config = {"from_attributes": True}


class DatasetSummary(BaseModel):
    dataset_id: uuid.UUID
    filename: str
    upload_ts: datetime
    row_count: int
    is_active: bool

    model_config = {"from_attributes": True}
