"""
Contact Volume Forecasting Engine
Two-stage approach: monthly de-seasonalisation + Holt-Winters weekly model
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.seasonal import seasonal_decompose
import warnings
import holidays
warnings.filterwarnings('ignore')


class ContactForecaster:
    """Multi-channel contact volume forecasting with rolling 15-month predictions."""

    def __init__(self):
        self.models = {}
        self.forecasts = {}
        self.historical_data = None
        self.actuals_data = None
        self.bank_holiday_config = {}
        self.monthly_volumes = {}

    # -------------------------------------------------------------------------
    # Data loading
    # -------------------------------------------------------------------------

    def load_data(self, excel_path, sheet_name='Data'):
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date')
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
            country_holidays = holidays.country_holidays(country_code)
            all_holidays = []
            for year in range(start_year, end_year + 1):
                current = datetime(year, 1, 1)
                while current.year == year:
                    if current in country_holidays:
                        all_holidays.append(pd.Timestamp(current))
                    current += timedelta(days=1)
            return sorted(list(set(all_holidays)))
        except Exception as e:
            print(f"Holiday lookup failed for {country_code}: {e}")
            return self._get_fallback_holidays(start_year, end_year)

    def _get_fallback_holidays(self, start_year, end_year):
        out = []
        for year in range(start_year, end_year + 1):
            out += [pd.Timestamp(f'{year}-01-01'), pd.Timestamp(f'{year}-12-25')]
        return out

    # -------------------------------------------------------------------------
    # Monthly volume targets
    # -------------------------------------------------------------------------

    def set_monthly_volumes(self, channel, monthly_data):
        if isinstance(monthly_data, pd.DataFrame):
            d = {}
            for _, row in monthly_data.iterrows():
                d[pd.to_datetime(row['Month']).strftime('%Y-%m')] = row['Volume']
            self.monthly_volumes[channel] = d
        else:
            self.monthly_volumes[channel] = monthly_data

    # -------------------------------------------------------------------------
    # Monthly seasonality helpers
    # -------------------------------------------------------------------------

    def _compute_monthly_factors(self, ts: pd.Series) -> dict:
        """Compute multiplicative monthly seasonal indices from a time series.

        Returns a dict {month_int: factor} where factor = monthly_avg / overall_avg.
        Missing months default to 1.0.
        """
        monthly_avg = ts.groupby(ts.index.month).mean()
        overall_avg = ts.mean()
        factors = {}
        for m in range(1, 13):
            factors[m] = float(monthly_avg[m] / overall_avg) if m in monthly_avg.index else 1.0
        return factors

    def _apply_monthly_factors(self, ts: pd.Series, factors: dict) -> pd.Series:
        """Divide a series by its monthly factors (de-seasonalise)."""
        out = ts.copy().astype(float)
        for m, f in factors.items():
            mask = out.index.month == m
            if f > 0:
                out[mask] = out[mask] / f
        return out

    def _reapply_monthly_factors(self, df: pd.DataFrame, factors: dict,
                                  date_col='ds') -> pd.DataFrame:
        """Multiply forecast columns (yhat, yhat_lower, yhat_upper) by monthly factors."""
        df = df.copy()
        mf = df[date_col].dt.month.map(factors).fillna(1.0)
        for col in ['yhat', 'yhat_lower', 'yhat_upper']:
            if col in df.columns:
                df[col] = df[col] * mf
        return df

    # -------------------------------------------------------------------------
    # Training
    # -------------------------------------------------------------------------

    def train_model(self, channel, custom_seasonality=True):
        """Train the best Holt-Winters model for a channel using AIC selection.

        Pipeline:
          1. Winsorise outliers (IQR)
          2. Compute monthly seasonal factors & de-seasonalise
          3. Try 8 model configs (4 trend/seasonal combos × damped/not-damped)
          4. Select best AIC; fallback to trend-only if all fail
        """
        channel_data = self.historical_data[
            self.historical_data['Channel'] == channel
        ].copy()

        if len(channel_data) < 30:
            return False, f"Insufficient data for {channel} (need ≥ 30 days)"

        ts = channel_data.set_index('Date')['Volume'].astype(float)

        # 1. Winsorise
        q1, q3 = ts.quantile(0.25), ts.quantile(0.75)
        iqr = q3 - q1
        ts = ts.clip(lower=q1 - 1.5 * iqr, upper=q3 + 1.5 * iqr)

        # 2. Monthly seasonal factors
        monthly_factors = self._compute_monthly_factors(ts)
        ts_adj = self._apply_monthly_factors(ts, monthly_factors)
        # Ensure positive values for multiplicative models
        ts_adj = ts_adj.clip(lower=0.1)

        apply_holidays = channel in self.bank_holiday_config
        country_code = self.bank_holiday_config.get(channel)

        # 3. Try configs
        configs = [
            ('add', 'add', True),
            ('add', 'add', False),
            ('add', 'mul', True),
            ('add', 'mul', False),
            ('mul', 'add', True),
            ('mul', 'add', False),
            ('mul', 'mul', True),
            ('mul', 'mul', False),
        ]

        best_aic = np.inf
        best_model = None
        best_config = None

        print(f"\n── Training: {channel} ──")
        for trend, seasonal, damped in configs:
            try:
                m = ExponentialSmoothing(
                    ts_adj,
                    seasonal_periods=7,
                    trend=trend,
                    seasonal=seasonal,
                    damped_trend=damped,
                    freq='D',
                )
                fitted = m.fit(optimized=True)
                aic = fitted.aic
                flag = '★' if aic < best_aic else ' '
                print(f"  {flag} ({trend:3},{seasonal:3},damped={damped}): AIC={aic:.1f}")
                if aic < best_aic:
                    best_aic = aic
                    best_model = fitted
                    best_config = (trend, seasonal, damped)
            except Exception as e:
                print(f"    ({trend},{seasonal},damped={damped}): skipped — {e}")

        if best_model is not None:
            self.models[channel] = {
                'model': best_model,
                'last_date': ts.index[-1],
                'ts': ts,
                'ts_adj': ts_adj,
                'monthly_factors': monthly_factors,
                'apply_holidays': apply_holidays,
                'country_code': country_code,
                'config': best_config,
                'aic': best_aic,
            }
            print(f"  Selected: {best_config}, AIC={best_aic:.1f}")
            return True, f"Model trained for {channel} — {best_config}, AIC={best_aic:.1f}"

        # 4. Fallback: trend-only (no seasonal)
        try:
            m = ExponentialSmoothing(ts_adj, trend='add', seasonal=None,
                                     damped_trend=True, freq='D')
            fitted = m.fit(optimized=True)
            self.models[channel] = {
                'model': fitted,
                'last_date': ts.index[-1],
                'ts': ts,
                'ts_adj': ts_adj,
                'monthly_factors': monthly_factors,
                'apply_holidays': apply_holidays,
                'country_code': country_code,
                'config': ('add', None, True),
                'aic': fitted.aic,
            }
            return True, f"Model trained for {channel} (trend-only fallback)"
        except Exception as e2:
            return False, f"Error training model: {str(e2)}"

    # -------------------------------------------------------------------------
    # Forecast generation
    # -------------------------------------------------------------------------

    def generate_forecast(self, channel, months_ahead=15, start_date=None):
        """Generate a rolling forecast with simulation-based confidence intervals."""
        if channel not in self.models:
            return None, f"Model not trained for {channel}"

        md = self.models[channel]
        model = md['model']
        monthly_factors = md.get('monthly_factors', {m: 1.0 for m in range(1, 13)})

        if start_date is None:
            start_date = md['last_date']

        forecast_days = months_ahead * 30

        try:
            # Point forecast (on de-seasonalised scale)
            raw_fcast = model.forecast(steps=forecast_days)

            forecast_dates = pd.date_range(
                start=start_date + timedelta(days=1),
                periods=forecast_days,
                freq='D',
            )

            forecast_df = pd.DataFrame({'ds': forecast_dates, 'yhat': raw_fcast.values})

            # Confidence intervals via simulation (on de-seasonalised scale)
            try:
                sims = model.simulate(
                    nsimulations=forecast_days,
                    repetitions=1000,
                    error='add',
                )
                # sims shape: (forecast_days, 1000)
                forecast_df['yhat_lower'] = np.percentile(sims, 2.5, axis=1)
                forecast_df['yhat_upper'] = np.percentile(sims, 97.5, axis=1)
            except Exception:
                std_err = np.std(model.resid)
                forecast_df['yhat_lower'] = forecast_df['yhat'] - 1.96 * std_err
                forecast_df['yhat_upper'] = forecast_df['yhat'] + 1.96 * std_err

            # Re-apply monthly seasonal factors
            forecast_df = self._reapply_monthly_factors(forecast_df, monthly_factors)

            # Bank holidays
            if md['apply_holidays'] and md['country_code']:
                holiday_dates = self.get_bank_holidays(
                    md['country_code'],
                    forecast_dates.min().year,
                    forecast_dates.max().year,
                )
                is_holiday = forecast_df['ds'].isin(holiday_dates)
                forecast_df.loc[is_holiday, ['yhat', 'yhat_lower', 'yhat_upper']] = 0

            # Client monthly volume targets
            if channel in self.monthly_volumes:
                forecast_df = self._apply_monthly_distribution(forecast_df, channel)

            # Clip negatives
            for col in ['yhat', 'yhat_lower', 'yhat_upper']:
                forecast_df[col] = forecast_df[col].clip(lower=0)

            self.forecasts[channel] = forecast_df
            return forecast_df, "Forecast generated successfully"

        except Exception as e:
            return None, f"Error generating forecast: {str(e)}"

    # -------------------------------------------------------------------------
    # Back-test (last N days held out)
    # -------------------------------------------------------------------------

    def backtest(self, channel, holdout_days=90):
        """Train on historical minus holdout, forecast holdout, compare to actual.

        Returns a DataFrame with columns: ds, actual, predicted.
        """
        if channel not in self.models:
            return None

        md = self.models[channel]
        ts = md['ts']  # winsorised, original scale

        if len(ts) <= holdout_days + 14:
            return None

        train_ts = ts.iloc[:-holdout_days]
        test_ts = ts.iloc[-holdout_days:]

        monthly_factors = self._compute_monthly_factors(train_ts)
        train_adj = self._apply_monthly_factors(train_ts, monthly_factors).clip(lower=0.1)

        trend, seasonal, damped = md.get('config', ('add', 'add', True))

        try:
            m = ExponentialSmoothing(
                train_adj,
                seasonal_periods=7,
                trend=trend,
                seasonal=seasonal,
                damped_trend=damped,
                freq='D',
            )
            fitted = m.fit(optimized=True)
            preds_adj = fitted.forecast(steps=holdout_days)

            # Re-apply monthly factors
            mf = np.array([monthly_factors.get(d.month, 1.0) for d in test_ts.index])
            preds = preds_adj.values * mf

            result = pd.DataFrame({
                'ds': test_ts.index,
                'actual': test_ts.values,
                'predicted': preds,
            })
            result['error_pct'] = (
                np.abs(result['actual'] - result['predicted']) / result['actual'].replace(0, np.nan) * 100
            )
            return result

        except Exception as e:
            print(f"Backtest failed for {channel}: {e}")
            return None

    def get_backtest_metrics(self, channel, holdout_days=90):
        """Return dict with MAPE, MAE, RMSE from backtest."""
        bt = self.backtest(channel, holdout_days)
        if bt is None or len(bt) == 0:
            return None
        actual = bt['actual']
        predicted = bt['predicted']
        mape = float(bt['error_pct'].mean())
        mae = float(np.mean(np.abs(actual - predicted)))
        rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
        return {'MAPE': mape, 'MAE': mae, 'RMSE': rmse, 'holdout_days': holdout_days}

    # -------------------------------------------------------------------------
    # Monthly distribution (client targets)
    # -------------------------------------------------------------------------

    def _apply_monthly_distribution(self, forecast, channel):
        monthly_targets = self.monthly_volumes[channel]
        forecast = forecast.copy()
        forecast['_month'] = forecast['ds'].dt.strftime('%Y-%m')

        for month_str, target_volume in monthly_targets.items():
            mask = forecast['_month'] == month_str
            if not mask.any():
                continue
            current_total = forecast.loc[mask, 'yhat'].sum()
            if current_total > 0:
                sf = target_volume / current_total
                forecast.loc[mask, 'yhat'] *= sf
                forecast.loc[mask, 'yhat_lower'] *= sf
                forecast.loc[mask, 'yhat_upper'] *= sf

        return forecast.drop('_month', axis=1)

    # -------------------------------------------------------------------------
    # Blend actuals with forecast
    # -------------------------------------------------------------------------

    def blend_actuals_with_forecast(self, channel, actuals_df=None):
        if actuals_df is not None and len(actuals_df) > 0:
            last_actual_date = actuals_df['Date'].max()
            forecast, _ = self.generate_forecast(channel, months_ahead=15,
                                                  start_date=last_actual_date)
            if forecast is None:
                return None

            actuals_fmt = actuals_df.rename(columns={'Date': 'ds', 'Volume': 'yhat'})
            actuals_fmt['is_actual'] = True
            forecast['is_actual'] = False
            forecast_filt = forecast[forecast['ds'] > last_actual_date]

            return pd.concat([
                actuals_fmt[['ds', 'yhat', 'is_actual']],
                forecast_filt[['ds', 'yhat', 'yhat_lower', 'yhat_upper', 'is_actual']],
            ], ignore_index=True)
        else:
            if channel in self.forecasts:
                fc = self.forecasts[channel].copy()
                fc['is_actual'] = False
                return fc
            return None

    # -------------------------------------------------------------------------
    # Aggregation helpers
    # -------------------------------------------------------------------------

    def get_weekly_aggregates(self, channel, year=None):
        cd = self.historical_data[self.historical_data['Channel'] == channel].copy()
        if year is not None:
            cd = cd[cd['Date'].dt.year == year]
        cd['Week'] = cd['Date'].dt.isocalendar().week
        cd['Year'] = cd['Date'].dt.year
        return cd.groupby(['Year', 'Week'])['Volume'].sum().reset_index()

    def compare_weeks(self, channel, week_numbers, years=None):
        if years is None:
            years = [2024, 2025, 2026]
        rows = []
        for year in years:
            wd = self.get_weekly_aggregates(channel, year)
            for week in week_numbers:
                wdata = wd[wd['Week'] == week]
                if not wdata.empty:
                    rows.append({'Year': year, 'Week': week,
                                 'Volume': wdata['Volume'].values[0]})
        return pd.DataFrame(rows)

    def calculate_accuracy_metrics(self, channel, actual_df):
        if channel not in self.forecasts:
            return None
        forecast = self.forecasts[channel]
        merged = actual_df.merge(forecast[['ds', 'yhat']],
                                 left_on='Date', right_on='ds', how='inner')
        if len(merged) == 0:
            return None
        actual, predicted = merged['Volume'], merged['yhat']
        mape = np.mean(np.abs((actual - predicted) / actual)) * 100
        rmse = np.sqrt(np.mean((actual - predicted) ** 2))
        mae = np.mean(np.abs(actual - predicted))
        return {'MAPE': mape, 'RMSE': rmse, 'MAE': mae, 'Sample_Size': len(merged)}

    def get_seasonality_insights(self, channel):
        if channel not in self.models:
            return None
        ts = self.models[channel]['ts']
        try:
            decomp = seasonal_decompose(ts, model='additive', period=7,
                                        extrapolate_trend='freq')
            return {
                'weekly': pd.DataFrame({'ds': decomp.seasonal.index,
                                        'weekly': decomp.seasonal.values}),
                'trend': pd.DataFrame({'ds': decomp.trend.index,
                                       'trend': decomp.trend.values}),
                'yearly': None,
            }
        except Exception:
            try:
                trend = pd.DataFrame({
                    'ds': ts.index,
                    'trend': ts.rolling(window=7, center=True).mean().values,
                })
                return {'weekly': None, 'trend': trend, 'yearly': None}
            except Exception:
                return None

    def get_available_countries(self):
        return {
            'US': 'United States', 'GB': 'United Kingdom', 'FR': 'France',
            'DE': 'Germany', 'ES': 'Spain', 'IT': 'Italy', 'MA': 'Morocco',
            'CA': 'Canada', 'AU': 'Australia', 'JP': 'Japan', 'CN': 'China',
            'IN': 'India', 'BR': 'Brazil', 'MX': 'Mexico', 'NL': 'Netherlands',
            'BE': 'Belgium', 'CH': 'Switzerland', 'AT': 'Austria', 'SE': 'Sweden',
            'NO': 'Norway', 'DK': 'Denmark', 'FI': 'Finland', 'PL': 'Poland',
            'PT': 'Portugal', 'IE': 'Ireland', 'NZ': 'New Zealand', 'SG': 'Singapore',
            'AE': 'United Arab Emirates', 'SA': 'Saudi Arabia',
            'ZA': 'South Africa', 'EG': 'Egypt',
        }
