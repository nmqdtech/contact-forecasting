import uuid
from datetime import date, datetime

from pydantic import BaseModel, field_validator, model_validator


class HiringWaveCreate(BaseModel):
    channel: str
    start_date: date
    end_date: date
    junior_count: int
    total_agents: int
    label: str | None = None

    @model_validator(mode="after")
    def validate_dates_and_counts(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.junior_count < 0:
            raise ValueError("junior_count must be non-negative")
        if self.total_agents <= 0:
            raise ValueError("total_agents must be positive")
        if self.junior_count > self.total_agents:
            raise ValueError("junior_count cannot exceed total_agents")
        return self


class HiringWaveOut(BaseModel):
    id: uuid.UUID
    channel: str
    start_date: date
    end_date: date
    junior_count: int
    total_agents: int
    junior_ratio: float
    label: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
