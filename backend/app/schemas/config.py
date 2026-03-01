from pydantic import BaseModel, Field


class HolidayConfigRequest(BaseModel):
    channel: str
    country_code: str = Field(min_length=2, max_length=10)


class MonthlyTargetsRequest(BaseModel):
    channel: str
    targets: dict[str, float] = Field(
        description="Keys are 'YYYY-MM', values are monthly volumes"
    )


class ConfigResponse(BaseModel):
    holidays: dict[str, str]            # {channel: country_code}
    targets: dict[str, dict[str, float]]  # {channel: {"YYYY-MM": volume}}


class SummaryRow(BaseModel):
    channel: str
    hist_avg_daily: float
    forecast_avg_daily: float
    change_pct: float
    total_15m: float
    peak_month: str
    trough_month: str
    has_holidays: bool
    has_targets: bool
