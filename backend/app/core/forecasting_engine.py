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
        self.aht_models: dict = {}       # channel → {model, last_date, has_junior}

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

        # Prophet dataframe — strip zero-volume rows (multiplicative mode breaks on zeros)
        prophet_df = pd.DataFrame(
            {
                "ds": pd.to_datetime(channel_data["Date"]),
                "y": channel_data["Volume"].astype(float),
            }
        )
        zero_count = (prophet_df["y"] == 0).sum()
        prophet_df = prophet_df[prophet_df["y"] > 0].copy()
        if zero_count > 0:
            print(f"  Stripped {zero_count} zero-volume rows before Prophet fit")

        if len(prophet_df) < 20:
            return False, f"Insufficient non-zero data for {channel} after stripping zeros"

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
        # For short datasets use additive mode — multiplicative needs scale data
        seasonality_mode = "multiplicative" if date_span_days >= 180 else "additive"

        print(f"\n── Training: {channel} (Prophet) ──")
        print(
            f"  Closed days  : {[['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][d] for d in sorted(closed_dows)]}"
        )
        print(f"  Holidays     : {country_code or 'None'}")
        print(f"  Yearly seas. : {enable_yearly}  ({date_span_days} days of data)")
        print(f"  Mode         : {seasonality_mode}")

        def _build_prophet(mode: str) -> "Prophet":
            m = Prophet(
                yearly_seasonality=enable_yearly,
                weekly_seasonality=True,
                daily_seasonality=False,
                seasonality_mode=mode,
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=10.0,
                n_changepoints=25,
                interval_width=0.95,
                holidays=holidays_df,
            )
            if custom_seasonality and date_span_days >= 60:
                m.add_seasonality(name="monthly", period=30.5, fourier_order=5)
            return m

        model = _build_prophet(seasonality_mode)
        try:
            model.fit(prophet_df)
        except (ValueError, RuntimeError) as exc:
            if seasonality_mode == "multiplicative":
                print(f"  Stan convergence failed ({exc}), retrying with additive mode")
                seasonality_mode = "additive"
                model = _build_prophet(seasonality_mode)
                try:
                    model.fit(prophet_df)
                except Exception as exc2:
                    return False, f"Prophet training failed for {channel}: {exc2}"
            else:
                return False, f"Prophet training failed for {channel}: {exc}"
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
            "config": ["prophet", seasonality_mode, f"yearly={enable_yearly}"],
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

        # Strip zeros from the prophet_df slice (same as main training)
        prophet_df_nz = prophet_df[prophet_df["y"] > 0].copy()
        if len(prophet_df_nz) <= holdout_days + 14:
            return None

        train_df = prophet_df_nz.iloc[:-holdout_days].copy()
        # test_df still uses original prophet_df to compare predictions against actuals
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
        bt_mode = "multiplicative" if date_span >= 180 else "additive"

        def _build_bt(mode: str):
            m = Prophet(
                yearly_seasonality=enable_yearly,
                weekly_seasonality=True,
                daily_seasonality=False,
                seasonality_mode=mode,
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=10.0,
                n_changepoints=25,
                interval_width=0.95,
                holidays=holidays_df,
            )
            if enable_monthly:
                m.add_seasonality(name="monthly", period=30.5, fourier_order=5)
            return m

        try:
            bt_model = _build_bt(bt_mode)
            try:
                bt_model.fit(train_df)
            except (ValueError, RuntimeError):
                if bt_mode == "multiplicative":
                    bt_mode = "additive"
                    bt_model = _build_bt(bt_mode)
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

    # -------------------------------------------------------------------------
    # AHT Model (Prophet with junior_ratio extra regressor)
    # -------------------------------------------------------------------------

    def train_aht_model(self, channel: str, aht_df: "pd.DataFrame") -> tuple[bool, str]:
        """Train a Prophet model for AHT forecasting.

        Args:
            channel: Channel name.
            aht_df: DataFrame with columns ['ds', 'y', 'junior_ratio'].
                    y = AHT in seconds (positive values only).
                    junior_ratio = 0.0–1.0 (fraction of junior agents).
        """
        from prophet import Prophet

        df = aht_df.copy()
        df = df[df["y"] > 0].copy()
        if len(df) < 14:
            return False, f"Insufficient AHT data for {channel} (need ≥ 14 days with non-zero AHT)"

        df["junior_ratio"] = pd.to_numeric(df["junior_ratio"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
        has_junior = (df["junior_ratio"] > 0).any()

        date_span = (df["ds"].max() - df["ds"].min()).days
        enable_yearly = date_span >= 180

        print(f"\n── AHT Training: {channel} ──")
        print(f"  Rows: {len(df)}  |  yearly={enable_yearly}  |  has_junior={has_junior}")

        model = Prophet(
            yearly_seasonality=enable_yearly,
            weekly_seasonality=True,
            daily_seasonality=False,
            seasonality_mode="additive",   # AHT is additive by nature
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=5.0,
            interval_width=0.95,
        )
        if has_junior:
            model.add_regressor("junior_ratio", prior_scale=10.0, standardize=True)

        try:
            model.fit(df)
        except Exception as exc:
            return False, f"AHT model training failed for {channel}: {exc}"

        self.aht_models[channel] = {
            "model": model,
            "last_date": df["ds"].max(),
            "has_junior": has_junior,
        }
        print("  AHT Prophet model fitted successfully.")
        return True, f"AHT model trained for {channel}"

    def generate_aht_forecast(
        self,
        channel: str,
        months_ahead: int = 15,
        start_date=None,
        future_junior_ratios: "dict[str, float] | None" = None,
        min_aht: float | None = None,
        max_aht: float | None = None,
    ) -> tuple["pd.DataFrame | None", str]:
        """Generate AHT forecast. Returns DataFrame with ['ds', 'aht_yhat']."""
        if channel not in self.aht_models:
            return None, f"AHT model not trained for {channel}"

        md = self.aht_models[channel]
        model = md["model"]

        if start_date is None:
            start_date = md["last_date"]

        forecast_days = months_ahead * 30
        forecast_dates = pd.date_range(
            start=start_date + timedelta(days=1), periods=forecast_days, freq="D"
        )
        future_df = pd.DataFrame({"ds": forecast_dates})

        if md["has_junior"]:
            if future_junior_ratios:
                future_df["junior_ratio"] = future_df["ds"].dt.strftime("%Y-%m-%d").map(
                    lambda d: future_junior_ratios.get(d, 0.0)
                ).fillna(0.0)
            else:
                future_df["junior_ratio"] = 0.0

        try:
            raw = model.predict(future_df)
            result = raw[["ds", "yhat"]].copy()
            result.rename(columns={"yhat": "aht_yhat"}, inplace=True)
            result["aht_yhat"] = result["aht_yhat"].clip(lower=1.0)   # AHT ≥ 1s
            if min_aht is not None:
                result["aht_yhat"] = result["aht_yhat"].clip(lower=min_aht)
            if max_aht is not None:
                result["aht_yhat"] = result["aht_yhat"].clip(upper=max_aht)
            return result, "AHT forecast generated"
        except Exception as exc:
            return None, f"AHT forecast failed for {channel}: {exc}"

    # -------------------------------------------------------------------------
    # 30-minute resampling for NICE IEX export
    # -------------------------------------------------------------------------

    @staticmethod
    def resample_to_30min(
        volume_series: "pd.Series",
        aht_series: "pd.Series",
        hourly_weights: "dict[int, float] | None" = None,
    ) -> "pd.DataFrame":
        """Resample daily volume + AHT into 48 half-hour slots per day.

        Args:
            volume_series: pd.Series indexed by date (daily contact totals).
            aht_series:    pd.Series indexed by date (daily AHT in seconds).
            hourly_weights: dict {hour 0-23: fraction} summing to 1.0.
                            Defaults to uniform (1/24 per hour).

        Returns:
            DataFrame with columns [ds (datetime), contacts (int), aht_seconds (float)].
        """
        if hourly_weights is None:
            hourly_weights = {h: 1.0 / 24 for h in range(24)}

        # Normalise weights to sum to 1
        total_w = sum(hourly_weights.values()) or 1.0
        weights = {h: w / total_w for h, w in hourly_weights.items()}

        # Convert series to dict for O(1) lookup
        vol_map = volume_series.to_dict()
        aht_map = aht_series.to_dict() if aht_series is not None else {}

        # Build adjacent-date AHT list for linear interpolation between days
        dates = sorted(vol_map.keys())
        aht_by_date: dict = {d: float(aht_map.get(d, 0.0) or 0.0) for d in dates}

        rows = []
        for i, date in enumerate(dates):
            daily_vol = float(vol_map[date])
            aht_today = aht_by_date.get(date, 0.0)

            # For linear AHT interpolation: blend toward next day at end of day
            if i < len(dates) - 1:
                next_date = dates[i + 1]
                aht_next = aht_by_date.get(next_date, aht_today)
            else:
                aht_next = aht_today

            for hour in range(24):
                hour_weight = weights.get(hour, 1.0 / 24)
                hour_vol = daily_vol * hour_weight  # distributive split

                # Split into two 30-min slots
                for half in range(2):
                    slot_dt = pd.Timestamp(date) + pd.Timedelta(hours=hour, minutes=half * 30)

                    # Linear interpolation for AHT across the full day
                    # fraction = slot index (0..47) / 48 blends today→tomorrow
                    slot_idx = hour * 2 + half
                    frac = slot_idx / 48.0
                    aht_slot = aht_today * (1 - frac) + aht_next * frac if aht_today > 0 else 0.0

                    rows.append({
                        "ds": slot_dt,
                        "contacts": max(0, round(hour_vol / 2)),
                        "aht_seconds": round(aht_slot, 2),
                    })

        return pd.DataFrame(rows, columns=["ds", "contacts", "aht_seconds"])

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
