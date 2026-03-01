from datetime import date

from pydantic import BaseModel


class ForecastPoint(BaseModel):
    date: date
    yhat: float
    yhat_lower: float
    yhat_upper: float


class ModelInfo(BaseModel):
    config: list | None = None        # ["add","add",true]
    aic: float | None = None
    backtest_mape: float | None = None
    backtest_mae: float | None = None
    monthly_factors: dict | None = None   # {"1":0.99,...}


class ForecastResponse(BaseModel):
    channel: str
    model: ModelInfo
    data: list[ForecastPoint]


class MonthlyPoint(BaseModel):
    month: str   # 'YYYY-MM'
    total: float


class MonthlyForecastPoint(BaseModel):
    month: str
    total: float
    lower: float
    upper: float


class MonthlyForecastResponse(BaseModel):
    channel: str
    historical: list[MonthlyPoint]
    forecast: list[MonthlyForecastPoint]


class BacktestPoint(BaseModel):
    date: date
    actual: float
    predicted: float
    error_pct: float | None = None


class BacktestMetrics(BaseModel):
    mape: float
    mae: float
    rmse: float
    holdout_days: int


class BacktestResponse(BaseModel):
    channel: str
    metrics: BacktestMetrics
    data: list[BacktestPoint]


class SeasonalityResponse(BaseModel):
    channel: str
    monthly_factors: dict        # {"1": 0.99, ..., "12": 1.27}
    weekly_pattern: list[dict]   # [{"day":"Monday","effect":12.3}, ...]
