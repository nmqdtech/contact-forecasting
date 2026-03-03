"""
Contact Volume Forecasting Engine
Prophet-based: weekly + yearly + custom monthly seasonality, multiplicative mode.
Smart closed-day detection per channel. Bank holiday awareness.
"""

import logging
import warnings
from datetime import datetime, timedelta

import holidays as hols_lib
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose

warnings.filterwarnings("ignore")
logging.getLogger("prophet").setLevel(logging.WARNING)
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)


class ContactForecaster:
    """Multi-channel contact volume forecasting with Prophet."""

    def __init__(self):
        self.models = {}
        self.forecasts = {}
        self.historical_data = None
        self.actuals_data = None
        self.bank_holiday_config = {}
        self.monthly_volumes = {}
        self._backtest_cache: dict = {}  # channel → bt DataFrame

    # -------------------------------------------------------------------------
    # Data loading (legacy helper kept for compatibility)
    # -------------------------------------------------------------------------

    def load_data(self, excel_path, sheet_name="Data"):
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.sort_values("Date")
            self.historical_data = df
            return True, "Data loaded successfully"
        except Exception as e:
            return False, f"Error loading data: {str(e)}"

    # -------------------------------------------------------------------------
    # Bank holidays
    # -------------------------------------------------------------------------

    def configure_bank_holidays(self, channel, country_code):
        self.bank_holiday_config[channel] = country_code

    def get_bank_holidays(self, country_code, start_year, end_year):
        try:
            country_hols = hols_lib.country_holidays(country_code)
            out: list[pd.Timestamp] = []
            for year in range(start_year, end_year + 1):
                current = datetime(year, 1, 1)
                while current.year == year:
                    if current in country_hols:
                        out.append(pd.Timestamp(current))
                    current += timedelta(days=1)
            return sorted(set(out))
        except Exception as exc:
            print(f"Holiday lookup failed for {country_code}: {exc}")
            return self._get_fallback_holidays(start_year, end_year)

    def _get_fallback_holidays(self, start_year, end_year):
        out = []
        for year in range(start_year, end_year + 1):
            out += [pd.Timestamp(f"{year}-01-01"), pd.Timestamp(f"{year}-12-25")]
        return out

    # -------------------------------------------------------------------------
    # Monthly volume targets
    # -------------------------------------------------------------------------

    def set_monthly_volumes(self, channel, monthly_data):
        if isinstance(monthly_data, pd.DataFrame):
            d = {}
            for _, row in monthly_data.iterrows():
                d[pd.to_datetime(row["Month"]).strftime("%Y-%m")] = row["Volume"]
            self.monthly_volumes[channel] = d
        else:
            self.monthly_volumes[channel] = monthly_data

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _compute_monthly_factors(self, ts: pd.Series) -> dict:
        monthly_avg = ts.groupby(ts.index.month).mean()
        overall_avg = ts.mean()
        if overall_avg == 0:
            return {m: 1.0 for m in range(1, 13)}
        return {
            m: float(monthly_avg[m] / overall_avg) if m in monthly_avg.index else 1.0
            for m in range(1, 13)
        }

    def _detect_closed_days(self, channel_data: pd.DataFrame) -> set[int]:
        """Return set of weekday numbers (0=Mon … 6=Sun) where channel is closed.

        A day is considered closed if it never appears in the data OR if its
        average volume is < 2% of the overall daily average.
        """
        dates = pd.to_datetime(channel_data["Date"])
        dows_present = set(dates.dt.dayofweek.unique())
        closed = set(range(7)) - dows_present  # days never seen → always closed

        if dows_present:
            cd = channel_data.copy()
            cd["_dow"] = dates.dt.dayofweek
            avg_by_dow = cd.groupby("_dow")["Volume"].mean()
            overall_avg = cd["Volume"].mean()
            if overall_avg > 0:
                for dow, avg in avg_by_dow.items():
                    if avg < 0.02 * overall_avg:
                        closed.add(dow)
        return closed

    def _build_holidays_df(self, country_code: str, min_year: int, max_year: int):
        """Return Prophet-style holidays DataFrame or None."""
        holiday_dates = self.get_bank_holidays(country_code, min_year, max_year)
        if not holiday_dates:
            return None
        return pd.DataFrame(
            {
                "holiday": "bank_holiday",
                "ds": pd.to_datetime(holiday_dates),
                "lower_window": 0,
                "upper_window": 0,
            }
        )

    def _apply_monthly_distribution(self, forecast: pd.DataFrame, channel: str) -> pd.DataFrame:
        monthly_targets = self.monthly_volumes[channel]
        forecast = forecast.copy()
        forecast["_month"] = forecast["ds"].dt.strftime("%Y-%m")
        for month_str, target_volume in monthly_targets.items():
            mask = forecast["_month"] == month_str
            if not mask.any():
                continue
            current_total = forecast.loc[mask, "yhat"].sum()
            if current_total > 0:
                sf = target_volume / current_total
                forecast.loc[mask, "yhat"] *= sf
                forecast.loc[mask, "yhat_lower"] *= sf
                forecast.loc[mask, "yhat_upper"] *= sf
        return forecast.drop("_month", axis=1)

    def _zero_closed_and_holidays(
        self,
        forecast_df: pd.DataFrame,
        closed_dows: set[int],
        apply_holidays: bool,
        country_code: str | None,
    ) -> pd.DataFrame:
        """Zero out forecast for closed days and bank holidays."""
        df = forecast_df.copy()
        cols = ["yhat", "yhat_lower", "yhat_upper"]

        if closed_dows:
            mask = df["ds"].dt.dayofweek.isin(closed_dows)
            df.loc[mask, cols] = 0.0

        if apply_holidays and country_code:
            min_year = df["ds"].dt.year.min()
            max_year = df["ds"].dt.year.max()
            holiday_dates = self.get_bank_holidays(country_code, min_year, max_year)
            if holiday_dates:
                mask = df["ds"].isin(holiday_dates)
                df.loc[mask, cols] = 0.0

        return df

    # -------------------------------------------------------------------------
    # Training
    # -------------------------------------------------------------------------

    def train_model(self, channel, custom_seasonality=True):
        from prophet import Prophet  # lazy import — cmdstan is pre-warmed in Docker

        channel_data = (
            self.historical_data[self.historical_data["Channel"] == channel]
            .copy()
            .sort_values("Date")
        )

        if len(channel_data) < 30:
            return False, f"Insufficient data for {channel} (need ≥ 30 days)"

        # Closed-day detection (days of week where channel never operates)
        closed_dows = self._detect_closed_days(channel_data)

        # Monthly factors (stored for metadata / display only)
        ts = channel_data.set_index("Date")["Volume"].astype(float)
        monthly_factors = self._compute_monthly_factors(ts)

        # Prophet dataframe — use raw data, no reindexing needed
        prophet_df = pd.DataFrame(
            {
                "ds": pd.to_datetime(channel_data["Date"]),
                "y": channel_data["Volume"].astype(float),
            }
        )

        apply_holidays = channel in self.bank_holiday_config
        country_code = self.bank_holiday_config.get(channel)

        # Build holidays for Prophet (teach model about holiday dips/spikes)
        holidays_df = None
        if apply_holidays and country_code:
            min_year = prophet_df["ds"].dt.year.min()
            max_year = prophet_df["ds"].dt.year.max() + 2
            holidays_df = self._build_holidays_df(country_code, min_year, max_year)

        # Decide whether to enable yearly seasonality (need ≥ 6 months)
        date_span_days = (channel_data["Date"].max() - channel_data["Date"].min()).days
        enable_yearly = date_span_days >= 180

        print(f"\n── Training: {channel} (Prophet) ──")
        print(
            f"  Closed days  : {[['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][d] for d in sorted(closed_dows)]}"
        )
        print(f"  Holidays     : {country_code or 'None'}")
        print(f"  Yearly seas. : {enable_yearly}  ({date_span_days} days of data)")

        model = Prophet(
            yearly_seasonality=enable_yearly,
            weekly_seasonality=True,
            daily_seasonality=False,
            seasonality_mode="multiplicative",   # scales with volume level
            changepoint_prior_scale=0.05,        # moderate trend flexibility
            seasonality_prior_scale=10.0,        # allow seasonality to be expressive
            interval_width=0.95,
            holidays=holidays_df,
        )

        # Custom monthly Fourier seasonality (captures month-of-year patterns)
        if custom_seasonality and date_span_days >= 60:
            model.add_seasonality(name="monthly", period=30.5, fourier_order=5)

        try:
            model.fit(prophet_df)
        except Exception as exc:
            return False, f"Prophet training failed for {channel}: {exc}"

        self.models[channel] = {
            "model": model,
            "last_date": channel_data["Date"].max(),
            "ts": ts,
            "prophet_df": prophet_df,
            "monthly_factors": monthly_factors,
            "apply_holidays": apply_holidays,
            "country_code": country_code,
            "closed_dows": closed_dows,
            "enable_yearly": enable_yearly,
            "custom_seasonality": custom_seasonality and date_span_days >= 60,
            # service compatibility fields
            "config": ["prophet", "multiplicative", f"yearly={enable_yearly}"],
            "aic": 0.0,  # AIC not applicable for Prophet
        }

        self._backtest_cache.pop(channel, None)  # invalidate old cache
        print("  Prophet model fitted successfully.")
        return True, f"Prophet model trained for {channel}"

    # -------------------------------------------------------------------------
    # Forecast generation
    # -------------------------------------------------------------------------

    def generate_forecast(self, channel, months_ahead=15, start_date=None):
        if channel not in self.models:
            return None, f"Model not trained for {channel}"

        md = self.models[channel]
        model = md["model"]

        if start_date is None:
            start_date = md["last_date"]

        forecast_days = months_ahead * 30
        forecast_dates = pd.date_range(
            start=start_date + timedelta(days=1), periods=forecast_days, freq="D"
        )

        try:
            future_df = pd.DataFrame({"ds": forecast_dates})
            raw = model.predict(future_df)
            forecast_df = raw[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()

            # Zero closed days + holidays
            forecast_df = self._zero_closed_and_holidays(
                forecast_df,
                md["closed_dows"],
                md["apply_holidays"],
                md["country_code"],
            )

            # Monthly distribution override (client targets)
            if channel in self.monthly_volumes:
                forecast_df = self._apply_monthly_distribution(forecast_df, channel)

            # Clip negatives
            for col in ["yhat", "yhat_lower", "yhat_upper"]:
                forecast_df[col] = forecast_df[col].clip(lower=0)

            self.forecasts[channel] = forecast_df
            return forecast_df, "Forecast generated successfully"

        except Exception as exc:
            return None, f"Error generating forecast: {str(exc)}"

    # -------------------------------------------------------------------------
    # Back-test (retrain on train split for honest evaluation)
    # -------------------------------------------------------------------------

    def backtest(self, channel, holdout_days=90):
        # Return cached result if available
        if channel in self._backtest_cache:
            return self._backtest_cache[channel]

        if channel not in self.models:
            return None

        from prophet import Prophet

        md = self.models[channel]
        prophet_df = md["prophet_df"]

        if len(prophet_df) <= holdout_days + 14:
            return None

        train_df = prophet_df.iloc[:-holdout_days].copy()
        test_df = prophet_df.iloc[-holdout_days:].copy()

        # Build holidays for the backtest period
        holidays_df = None
        if md["apply_holidays"] and md["country_code"]:
            min_year = train_df["ds"].dt.year.min()
            max_year = test_df["ds"].dt.year.max() + 1
            holidays_df = self._build_holidays_df(md["country_code"], min_year, max_year)

        date_span = (train_df["ds"].max() - train_df["ds"].min()).days
        enable_yearly = date_span >= 180
        enable_monthly = date_span >= 60

        try:
            bt_model = Prophet(
                yearly_seasonality=enable_yearly,
                weekly_seasonality=True,
                daily_seasonality=False,
                seasonality_mode="multiplicative",
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=10.0,
                interval_width=0.95,
                holidays=holidays_df,
            )
            if enable_monthly:
                bt_model.add_seasonality(name="monthly", period=30.5, fourier_order=5)

            bt_model.fit(train_df)

            future_df = pd.DataFrame({"ds": test_df["ds"].values})
            bt_raw = bt_model.predict(future_df)
            preds = bt_raw["yhat"].clip(lower=0).values

            # Zero closed days in holdout predictions
            if md["closed_dows"]:
                closed_mask = test_df["ds"].dt.dayofweek.isin(md["closed_dows"]).values
                preds[closed_mask] = 0.0

            result = pd.DataFrame(
                {
                    "ds": test_df["ds"].values,
                    "actual": test_df["y"].values,
                    "predicted": preds,
                }
            )
            result["error_pct"] = (
                np.abs(result["actual"] - result["predicted"])
                / result["actual"].replace(0, np.nan)
                * 100
            )

            self._backtest_cache[channel] = result
            return result

        except Exception as exc:
            print(f"Backtest failed for {channel}: {exc}")
            return None

    def get_backtest_metrics(self, channel, holdout_days=90):
        bt = self.backtest(channel, holdout_days)
        if bt is None or len(bt) == 0:
            return None
        actual = bt["actual"]
        predicted = bt["predicted"]
        mape = float(bt["error_pct"].mean())
        mae = float(np.mean(np.abs(actual - predicted)))
        rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
        return {"MAPE": mape, "MAE": mae, "RMSE": rmse, "holdout_days": holdout_days}

    # -------------------------------------------------------------------------
    # Blend actuals with forecast
    # -------------------------------------------------------------------------

    def blend_actuals_with_forecast(self, channel, actuals_df=None):
        if actuals_df is not None and len(actuals_df) > 0:
            last_actual_date = actuals_df["Date"].max()
            forecast, _ = self.generate_forecast(channel, months_ahead=15, start_date=last_actual_date)
            if forecast is None:
                return None
            actuals_fmt = actuals_df.rename(columns={"Date": "ds", "Volume": "yhat"})
            actuals_fmt["is_actual"] = True
            forecast["is_actual"] = False
            forecast_filt = forecast[forecast["ds"] > last_actual_date]
            return pd.concat(
                [
                    actuals_fmt[["ds", "yhat", "is_actual"]],
                    forecast_filt[["ds", "yhat", "yhat_lower", "yhat_upper", "is_actual"]],
                ],
                ignore_index=True,
            )
        else:
            if channel in self.forecasts:
                fc = self.forecasts[channel].copy()
                fc["is_actual"] = False
                return fc
            return None

    # -------------------------------------------------------------------------
    # Seasonality insights (still uses statsmodels for the decomposition display)
    # -------------------------------------------------------------------------

    def get_seasonality_insights(self, channel):
        if channel not in self.models:
            return None
        ts = self.models[channel]["ts"]
        try:
            decomp = seasonal_decompose(ts, model="additive", period=7, extrapolate_trend="freq")
            return {
                "weekly": pd.DataFrame({"ds": decomp.seasonal.index, "weekly": decomp.seasonal.values}),
                "trend": pd.DataFrame({"ds": decomp.trend.index, "trend": decomp.trend.values}),
                "yearly": None,
            }
        except Exception:
            try:
                trend = pd.DataFrame(
                    {"ds": ts.index, "trend": ts.rolling(window=7, center=True).mean().values}
                )
                return {"weekly": None, "trend": trend, "yearly": None}
            except Exception:
                return None

    # -------------------------------------------------------------------------
    # Misc helpers kept for API compatibility
    # -------------------------------------------------------------------------

    def get_weekly_aggregates(self, channel, year=None):
        cd = self.historical_data[self.historical_data["Channel"] == channel].copy()
        if year is not None:
            cd = cd[cd["Date"].dt.year == year]
        cd["Week"] = cd["Date"].dt.isocalendar().week
        cd["Year"] = cd["Date"].dt.year
        return cd.groupby(["Year", "Week"])["Volume"].sum().reset_index()

    def compare_weeks(self, channel, week_numbers, years=None):
        if years is None:
            years = [2024, 2025, 2026]
        rows = []
        for year in years:
            wd = self.get_weekly_aggregates(channel, year)
            for week in week_numbers:
                wdata = wd[wd["Week"] == week]
                if not wdata.empty:
                    rows.append({"Year": year, "Week": week, "Volume": wdata["Volume"].values[0]})
        return pd.DataFrame(rows)

    def get_available_countries(self):
        return {
            "US": "United States", "GB": "United Kingdom", "FR": "France",
            "DE": "Germany", "ES": "Spain", "IT": "Italy", "MA": "Morocco",
            "CA": "Canada", "AU": "Australia", "JP": "Japan", "CN": "China",
            "IN": "India", "BR": "Brazil", "MX": "Mexico", "NL": "Netherlands",
            "BE": "Belgium", "CH": "Switzerland", "AT": "Austria", "SE": "Sweden",
            "NO": "Norway", "DK": "Denmark", "FI": "Finland", "PL": "Poland",
            "PT": "Portugal", "IE": "Ireland", "NZ": "New Zealand", "SG": "Singapore",
            "AE": "United Arab Emirates", "SA": "Saudi Arabia",
            "ZA": "South Africa", "EG": "Egypt",
        }
