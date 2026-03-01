"""
Forecasting service: background training jobs and forecast/backtest retrieval.
"""
import asyncio
import uuid
from datetime import datetime, timezone

import pandas as pd
from fastapi import BackgroundTasks
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.forecasting_engine import ContactForecaster
from app.db.database import AsyncSessionLocal
from app.models.backtest_result import BacktestResult
from app.models.channel_config import ChannelConfig
from app.models.forecast import Forecast
from app.models.monthly_target import MonthlyTarget
from app.models.observation import ChannelObservation
from app.models.training_run import TrainingRun
from app.schemas.config import SummaryRow
from app.schemas.forecast import (
    BacktestMetrics,
    BacktestPoint,
    BacktestResponse,
    ForecastPoint,
    ForecastResponse,
    ModelInfo,
    MonthlyForecastPoint,
    MonthlyForecastResponse,
    MonthlyPoint,
    SeasonalityResponse,
)
from app.schemas.training import ChannelTrainingResult, TrainingJobStatus, TrainingRequest

_HOLDOUT_DAYS = 90


# ---------------------------------------------------------------------------
# Training orchestration
# ---------------------------------------------------------------------------


async def start_training_job(
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    request: TrainingRequest,
) -> uuid.UUID:
    """Create pending TrainingRun rows and enqueue the background task."""
    job_id = uuid.uuid4()
    run_ids: dict[str, uuid.UUID] = {}

    for channel in request.channels:
        run = TrainingRun(
            job_id=job_id,
            channel=channel,
            dataset_id=request.dataset_id,
            months_ahead=request.months_ahead,
            status="pending",
        )
        db.add(run)
        await db.flush()  # populate run.id
        run_ids[channel] = run.id

    await db.commit()

    background_tasks.add_task(
        run_training_job,
        job_id=job_id,
        dataset_id=request.dataset_id,
        channels=list(request.channels),
        months_ahead=request.months_ahead,
        run_ids=run_ids,
    )
    return job_id


async def run_training_job(
    job_id: uuid.UUID,
    dataset_id: uuid.UUID,
    channels: list[str],
    months_ahead: int,
    run_ids: dict[str, uuid.UUID],
) -> None:
    """Background task: train models, persist forecasts and backtest results."""
    async with AsyncSessionLocal() as db:
        # 1. Load observations for the requested dataset + channels
        obs_result = await db.execute(
            select(ChannelObservation)
            .where(ChannelObservation.dataset_id == dataset_id)
            .where(ChannelObservation.channel.in_(channels))
            .order_by(ChannelObservation.obs_date)
        )
        observations = obs_result.scalars().all()

        if not observations:
            for run_id in run_ids.values():
                await db.execute(
                    update(TrainingRun)
                    .where(TrainingRun.id == run_id)
                    .values(status="failed", error_message="No observations found in dataset")
                )
            await db.commit()
            return

        df = pd.DataFrame(
            [
                {
                    "Date": pd.Timestamp(obs.obs_date),
                    "Channel": obs.channel,
                    "Volume": float(obs.volume),
                }
                for obs in observations
            ]
        )

        # 2. Load holiday configs
        hol_result = await db.execute(
            select(ChannelConfig).where(ChannelConfig.channel.in_(channels))
        )
        holiday_configs = {
            c.channel: c.country_code
            for c in hol_result.scalars().all()
            if c.country_code
        }

        # 3. Load monthly targets
        tgt_result = await db.execute(
            select(MonthlyTarget).where(MonthlyTarget.channel.in_(channels))
        )
        monthly_targets: dict[str, dict[str, float]] = {}
        for t in tgt_result.scalars().all():
            monthly_targets.setdefault(t.channel, {})[t.month] = float(t.volume)

        # 4. Set up forecaster
        forecaster = ContactForecaster()
        forecaster.historical_data = df

        for channel, country_code in holiday_configs.items():
            forecaster.configure_bank_holidays(channel, country_code)

        for channel, targets in monthly_targets.items():
            forecaster.set_monthly_volumes(channel, targets)

        # 5. Train each channel
        for channel in channels:
            run_id = run_ids[channel]
            try:
                # Mark as running
                await db.execute(
                    update(TrainingRun)
                    .where(TrainingRun.id == run_id)
                    .values(status="running", started_at=datetime.now(timezone.utc))
                )
                await db.commit()

                # Train (CPU-bound)
                success, msg = await asyncio.to_thread(forecaster.train_model, channel)

                if not success:
                    await db.execute(
                        update(TrainingRun)
                        .where(TrainingRun.id == run_id)
                        .values(status="failed", error_message=msg)
                    )
                    await db.commit()
                    continue

                md = forecaster.models[channel]
                best_config = list(md["config"])  # tuple → list for JSONB
                best_aic = float(md["aic"])
                monthly_factors = {str(k): v for k, v in md["monthly_factors"].items()}

                # Generate forecast (CPU-bound)
                forecast_df, fmsg = await asyncio.to_thread(
                    forecaster.generate_forecast, channel, months_ahead
                )

                if forecast_df is None:
                    await db.execute(
                        update(TrainingRun)
                        .where(TrainingRun.id == run_id)
                        .values(status="failed", error_message=fmsg)
                    )
                    await db.commit()
                    continue

                # Backtest (CPU-bound)
                bt_df = await asyncio.to_thread(forecaster.backtest, channel, _HOLDOUT_DAYS)
                bt_metrics = forecaster.get_backtest_metrics(channel, _HOLDOUT_DAYS)

                # Deactivate previous active runs for this channel
                await db.execute(
                    update(TrainingRun)
                    .where(TrainingRun.channel == channel)
                    .where(TrainingRun.is_active == True)  # noqa: E712
                    .where(TrainingRun.id != run_id)
                    .values(is_active=False)
                )

                # Persist forecast rows
                forecast_rows = [
                    Forecast(
                        training_run_id=run_id,
                        channel=channel,
                        forecast_date=row["ds"].date(),
                        yhat=float(row["yhat"]),
                        yhat_lower=float(row["yhat_lower"]),
                        yhat_upper=float(row["yhat_upper"]),
                    )
                    for _, row in forecast_df.iterrows()
                ]
                db.add_all(forecast_rows)

                # Persist backtest result
                if bt_df is not None and bt_metrics is not None:
                    bt_data = [
                        {
                            "date": row["ds"].strftime("%Y-%m-%d"),
                            "actual": float(row["actual"]),
                            "predicted": float(row["predicted"]),
                            "error_pct": (
                                float(row["error_pct"])
                                if pd.notna(row["error_pct"])
                                else None
                            ),
                        }
                        for _, row in bt_df.iterrows()
                    ]
                    db.add(
                        BacktestResult(
                            training_run_id=run_id,
                            channel=channel,
                            holdout_days=_HOLDOUT_DAYS,
                            mape=bt_metrics.get("MAPE"),
                            mae=bt_metrics.get("MAE"),
                            rmse=bt_metrics.get("RMSE"),
                            data=bt_data,
                        )
                    )

                # Mark training run complete and active
                await db.execute(
                    update(TrainingRun)
                    .where(TrainingRun.id == run_id)
                    .values(
                        status="completed",
                        completed_at=datetime.now(timezone.utc),
                        model_config=best_config,
                        aic=best_aic,
                        monthly_factors=monthly_factors,
                        is_active=True,
                    )
                )
                await db.commit()

            except Exception as exc:  # noqa: BLE001
                try:
                    await db.rollback()
                    await db.execute(
                        update(TrainingRun)
                        .where(TrainingRun.id == run_id)
                        .values(status="failed", error_message=str(exc))
                    )
                    await db.commit()
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Status polling
# ---------------------------------------------------------------------------


async def get_job_status(db: AsyncSession, job_id: uuid.UUID) -> TrainingJobStatus | None:
    """Return aggregated status for all channels in a training job."""
    runs_result = await db.execute(
        select(TrainingRun).where(TrainingRun.job_id == job_id)
    )
    runs = runs_result.scalars().all()
    if not runs:
        return None

    # Fetch backtest MAPEs in one query
    run_ids = [r.id for r in runs]
    bt_result = await db.execute(
        select(BacktestResult).where(BacktestResult.training_run_id.in_(run_ids))
    )
    mape_map: dict[uuid.UUID, float] = {
        b.training_run_id: float(b.mape)
        for b in bt_result.scalars().all()
        if b.mape is not None
    }

    results = [
        ChannelTrainingResult(
            channel=run.channel,
            status=run.status,
            config=run.model_config,
            aic=float(run.aic) if run.aic is not None else None,
            backtest_mape=mape_map.get(run.id),
            message=run.error_message,
            started_at=run.started_at,
            completed_at=run.completed_at,
        )
        for run in runs
    ]

    total = len(runs)
    done = sum(1 for r in runs if r.status in ("completed", "failed"))
    statuses = {r.status for r in runs}

    if "running" in statuses:
        overall = "running"
    elif all(r.status == "completed" for r in runs):
        overall = "completed"
    elif all(r.status in ("completed", "failed") for r in runs):
        overall = "failed"
    else:
        overall = "pending"

    return TrainingJobStatus(
        job_id=job_id,
        status=overall,
        progress=done / total if total > 0 else 0.0,
        results=results,
    )


# ---------------------------------------------------------------------------
# Forecast retrieval
# ---------------------------------------------------------------------------


async def get_forecast(db: AsyncSession, channel: str) -> ForecastResponse | None:
    run_result = await db.execute(
        select(TrainingRun)
        .where(TrainingRun.channel == channel)
        .where(TrainingRun.is_active == True)  # noqa: E712
    )
    run = run_result.scalar_one_or_none()
    if run is None:
        return None

    bt_result = await db.execute(
        select(BacktestResult).where(BacktestResult.training_run_id == run.id)
    )
    bt = bt_result.scalar_one_or_none()

    fc_result = await db.execute(
        select(Forecast)
        .where(Forecast.training_run_id == run.id)
        .where(Forecast.channel == channel)
        .order_by(Forecast.forecast_date)
    )
    forecasts = fc_result.scalars().all()

    return ForecastResponse(
        channel=channel,
        model=ModelInfo(
            config=run.model_config,
            aic=float(run.aic) if run.aic is not None else None,
            backtest_mape=float(bt.mape) if bt and bt.mape is not None else None,
            backtest_mae=float(bt.mae) if bt and bt.mae is not None else None,
            monthly_factors=run.monthly_factors,
        ),
        data=[
            ForecastPoint(
                date=f.forecast_date,
                yhat=float(f.yhat or 0),
                yhat_lower=float(f.yhat_lower or 0),
                yhat_upper=float(f.yhat_upper or 0),
            )
            for f in forecasts
        ],
    )


async def get_monthly_forecast(
    db: AsyncSession, channel: str
) -> MonthlyForecastResponse | None:
    run_result = await db.execute(
        select(TrainingRun)
        .where(TrainingRun.channel == channel)
        .where(TrainingRun.is_active == True)  # noqa: E712
    )
    run = run_result.scalar_one_or_none()
    if run is None:
        return None

    # Historical observations
    obs_result = await db.execute(
        select(ChannelObservation)
        .where(ChannelObservation.dataset_id == run.dataset_id)
        .where(ChannelObservation.channel == channel)
        .order_by(ChannelObservation.obs_date)
    )
    observations = obs_result.scalars().all()

    historical: list[MonthlyPoint] = []
    if observations:
        hist_df = pd.DataFrame(
            [{"month": o.obs_date.strftime("%Y-%m"), "volume": float(o.volume)} for o in observations]
        )
        hist_monthly = hist_df.groupby("month")["volume"].sum().reset_index()
        historical = [
            MonthlyPoint(month=row["month"], total=row["volume"])
            for _, row in hist_monthly.iterrows()
        ]

    # Forecast rows
    fc_result = await db.execute(
        select(Forecast)
        .where(Forecast.training_run_id == run.id)
        .where(Forecast.channel == channel)
        .order_by(Forecast.forecast_date)
    )
    forecasts = fc_result.scalars().all()

    forecast_monthly: list[MonthlyForecastPoint] = []
    if forecasts:
        fc_df = pd.DataFrame(
            [
                {
                    "month": f.forecast_date.strftime("%Y-%m"),
                    "yhat": float(f.yhat or 0),
                    "yhat_lower": float(f.yhat_lower or 0),
                    "yhat_upper": float(f.yhat_upper or 0),
                }
                for f in forecasts
            ]
        )
        agg = fc_df.groupby("month").agg(
            total=("yhat", "sum"),
            lower=("yhat_lower", "sum"),
            upper=("yhat_upper", "sum"),
        ).reset_index()
        forecast_monthly = [
            MonthlyForecastPoint(
                month=row["month"],
                total=row["total"],
                lower=row["lower"],
                upper=row["upper"],
            )
            for _, row in agg.iterrows()
        ]

    return MonthlyForecastResponse(
        channel=channel,
        historical=historical,
        forecast=forecast_monthly,
    )


async def get_backtest(db: AsyncSession, channel: str) -> BacktestResponse | None:
    run_result = await db.execute(
        select(TrainingRun)
        .where(TrainingRun.channel == channel)
        .where(TrainingRun.is_active == True)  # noqa: E712
    )
    run = run_result.scalar_one_or_none()
    if run is None:
        return None

    bt_result = await db.execute(
        select(BacktestResult).where(BacktestResult.training_run_id == run.id)
    )
    bt = bt_result.scalar_one_or_none()
    if bt is None:
        return None

    points = [
        BacktestPoint(
            date=datetime.strptime(row["date"], "%Y-%m-%d").date(),
            actual=row["actual"],
            predicted=row["predicted"],
            error_pct=row.get("error_pct"),
        )
        for row in (bt.data or [])
    ]

    return BacktestResponse(
        channel=channel,
        metrics=BacktestMetrics(
            mape=float(bt.mape or 0),
            mae=float(bt.mae or 0),
            rmse=float(bt.rmse or 0),
            holdout_days=bt.holdout_days,
        ),
        data=points,
    )


async def get_seasonality(db: AsyncSession, channel: str) -> SeasonalityResponse | None:
    run_result = await db.execute(
        select(TrainingRun)
        .where(TrainingRun.channel == channel)
        .where(TrainingRun.is_active == True)  # noqa: E712
    )
    run = run_result.scalar_one_or_none()
    if run is None:
        return None

    obs_result = await db.execute(
        select(ChannelObservation)
        .where(ChannelObservation.dataset_id == run.dataset_id)
        .where(ChannelObservation.channel == channel)
        .order_by(ChannelObservation.obs_date)
    )
    observations = obs_result.scalars().all()

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekly_pattern: list[dict] = []

    if observations:
        obs_df = pd.DataFrame(
            [{"date": pd.Timestamp(o.obs_date), "volume": float(o.volume)} for o in observations]
        )
        obs_df["dayofweek"] = obs_df["date"].dt.dayofweek
        daily_avg = obs_df.groupby("dayofweek")["volume"].mean()
        overall_avg = obs_df["volume"].mean()
        for dow in range(7):
            avg = float(daily_avg.get(dow, overall_avg))
            effect = ((avg / overall_avg) - 1) * 100 if overall_avg > 0 else 0.0
            weekly_pattern.append({"day": day_names[dow], "effect": round(effect, 2)})

    monthly_factors = run.monthly_factors or {str(m): 1.0 for m in range(1, 13)}
    return SeasonalityResponse(
        channel=channel,
        monthly_factors=monthly_factors,
        weekly_pattern=weekly_pattern,
    )


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


async def get_summary_rows(db: AsyncSession) -> list[SummaryRow]:
    """Aggregate channel-level summary from active training runs."""
    runs_result = await db.execute(
        select(TrainingRun).where(TrainingRun.is_active == True)  # noqa: E712
    )
    runs = {r.channel: r for r in runs_result.scalars().all()}
    if not runs:
        return []

    # Holiday and target presence
    hol_result = await db.execute(select(ChannelConfig))
    hol_channels = {c.channel for c in hol_result.scalars().all() if c.country_code}

    tgt_result = await db.execute(select(MonthlyTarget))
    tgt_channels = {t.channel for t in tgt_result.scalars().all()}

    rows: list[SummaryRow] = []
    for channel, run in sorted(runs.items()):
        # Historical daily average
        obs_result = await db.execute(
            select(ChannelObservation.volume)
            .where(ChannelObservation.dataset_id == run.dataset_id)
            .where(ChannelObservation.channel == channel)
        )
        volumes = [float(v) for v in obs_result.scalars().all()]
        hist_avg = sum(volumes) / len(volumes) if volumes else 0.0

        # Forecast rows
        fc_result = await db.execute(
            select(Forecast)
            .where(Forecast.training_run_id == run.id)
            .where(Forecast.channel == channel)
            .order_by(Forecast.forecast_date)
        )
        fcs = fc_result.scalars().all()
        if not fcs:
            continue

        fc_yhats = [float(f.yhat or 0) for f in fcs]
        fc_avg = sum(fc_yhats) / len(fc_yhats) if fc_yhats else 0.0
        total_15m = sum(fc_yhats)
        change_pct = ((fc_avg / hist_avg) - 1) * 100 if hist_avg > 0 else 0.0

        monthly: dict[str, float] = {}
        for f in fcs:
            key = f.forecast_date.strftime("%Y-%m")
            monthly[key] = monthly.get(key, 0.0) + float(f.yhat or 0)

        peak_month = max(monthly, key=lambda k: monthly[k]) if monthly else ""
        trough_month = min(monthly, key=lambda k: monthly[k]) if monthly else ""

        rows.append(
            SummaryRow(
                channel=channel,
                hist_avg_daily=round(hist_avg, 2),
                forecast_avg_daily=round(fc_avg, 2),
                change_pct=round(change_pct, 2),
                total_15m=round(total_15m, 2),
                peak_month=peak_month,
                trough_month=trough_month,
                has_holidays=channel in hol_channels,
                has_targets=channel in tgt_channels,
            )
        )

    return rows
