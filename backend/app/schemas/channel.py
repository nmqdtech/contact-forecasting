import uuid
from datetime import date

from pydantic import BaseModel


class ChannelInfo(BaseModel):
    name: str
    row_count: int
    date_min: date
    date_max: date
    is_hourly: bool = False
    has_aht: bool = False


class HourlyPoint(BaseModel):
    hour: int        # 0–23
    avg_volume: float


class ObservationPoint(BaseModel):
    date: date
    volume: float


class MonthlyObservation(BaseModel):
    month: str   # 'YYYY-MM'
    total: float
