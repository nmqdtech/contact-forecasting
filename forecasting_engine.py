"""
Contact Volume Forecasting Engine - Lightweight Version
Uses statsmodels instead of Prophet for better compatibility
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
    """
    Multi-channel contact volume forecasting with rolling 15-month predictions
    """

    def __init__(self):
        self.models = {}
        self.forecasts = {}
        self.historical_data = None
        self.actuals_data = None
        self.bank_holiday_config = {}
        self.monthly_volumes = {}

    def load_data(self, excel_path, sheet_name='Data'):
        """Load historical data from Excel"""
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date')
            self.historical_data = df
            return True, "Data loaded successfully"
        except Exception as e:
            return False, f"Error loading data: {str(e)}"

    def configure_bank_holidays(self, channel, country_code):
        """Configure bank holidays for a specific channel"""
        self.bank_holiday_config[channel] = country_code

    def get_bank_holidays(self, country_code, start_year, end_year):
        """Get bank holidays for a country across multiple years"""
        try:
            country_holidays = holidays.country_holidays(country_code)

            all_holidays = []
            for year in range(start_year, end_year + 1):
                start_date = datetime(year, 1, 1)
                end_date = datetime(year, 12, 31)
                current_date = start_date

                while current_date <= end_date:
                    if current_date in country_holidays:
                        all_holidays.append(pd.Timestamp(current_date))
                    current_date += timedelta(days=1)

            return sorted(list(set(all_holidays)))

        except Exception as e:
            print(f"Error getting holidays for {country_code}: {e}")
            return self._get_fallback_holidays(start_year, end_year)

    def _get_fallback_holidays(self, start_year, end_year):
        """Fallback common holidays"""
        common_holidays = []
        for year in range(start_year, end_year + 1):
            common_holidays.extend([
                pd.Timestamp(f'{year}-01-01'),
                pd.Timestamp(f'{year}-12-25'),
            ])
        return common_holidays

    def set_monthly_volumes(self, channel, monthly_data):
        """Set monthly target volumes from client"""
        if isinstance(monthly_data, pd.DataFrame):
            monthly_dict = {}
            for _, row in monthly_data.iterrows():
                month_str = pd.to_datetime(row['Month']).strftime('%Y-%m')
                monthly_dict[month_str] = row['Volume']
            self.monthly_volumes[channel] = monthly_dict
        else:
            self.monthly_volumes[channel] = monthly_data

    def train_model(self, channel, custom_seasonality=True):
        """Train forecasting model for a specific channel"""
        channel_data = self.historical_data[
            self.historical_data['Channel'] == channel
        ].copy()

        if len(channel_data) < 30:
            return False, f"Insufficient data for {channel} (need at least 30 days)"

        # Prepare time series
        ts = channel_data.set_index('Date')['Volume']

        # Winsorize outliers using IQR
        Q1 = ts.quantile(0.25)
        Q3 = ts.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        ts = ts.clip(lower=lower_bound, upper=upper_bound)

        # Check if bank holidays should be applied
        apply_holidays = channel in self.bank_holiday_config
        country_code = self.bank_holiday_config.get(channel)

        # Try 4 model configurations in order of preference, pick best AIC
        configs = [('mul', 'mul'), ('add', 'mul'), ('mul', 'add'), ('add', 'add')]
        best_aic = np.inf
        best_model = None
        best_config = None

        print(f"\nTraining model for channel: {channel}")
        for trend, seasonal in configs:
            try:
                model = ExponentialSmoothing(
                    ts,
                    seasonal_periods=7,
                    trend=trend,
                    seasonal=seasonal,
                    freq='D'
                )
                fitted = model.fit(optimized=True)
                aic = fitted.aic
                print(f"  ({trend}, {seasonal}): AIC={aic:.1f}")
                if aic < best_aic:
                    best_aic = aic
                    best_model = fitted
                    best_config = (trend, seasonal)
            except Exception as e:
                print(f"  ({trend}, {seasonal}): failed — {e}")
                continue

        if best_model is not None:
            self.models[channel] = {
                'model': best_model,
                'last_date': ts.index[-1],
                'ts': ts,
                'apply_holidays': apply_holidays,
                'country_code': country_code,
                'config': best_config,
                'aic': best_aic,
            }
            print(f"  Selected: {best_config}, AIC={best_aic:.1f}")
            return True, f"Model trained for {channel} (config={best_config}, AIC={best_aic:.1f})"

        # Fallback: trend-only model
        try:
            model = ExponentialSmoothing(ts, trend='add', seasonal=None, freq='D')
            fitted_model = model.fit(optimized=True)

            self.models[channel] = {
                'model': fitted_model,
                'last_date': ts.index[-1],
                'ts': ts,
                'apply_holidays': apply_holidays,
                'country_code': country_code,
                'config': ('add', None),
                'aic': fitted_model.aic,
            }
            print(f"  Fallback trend-only: AIC={fitted_model.aic:.1f}")
            return True, f"Model trained for {channel} (trend-only fallback)"
        except Exception as e2:
            return False, f"Error training model: {str(e2)}"

    def generate_forecast(self, channel, months_ahead=15, start_date=None):
        """Generate rolling 15-month forecast"""
        if channel not in self.models:
            return None, f"Model not trained for {channel}"

        model_data = self.models[channel]
        model = model_data['model']

        if start_date is None:
            start_date = model_data['last_date']

        forecast_days = months_ahead * 30

        try:
            # Generate point forecast
            forecast = model.forecast(steps=forecast_days)

            forecast_dates = pd.date_range(
                start=start_date + timedelta(days=1),
                periods=forecast_days,
                freq='D'
            )

            forecast_df = pd.DataFrame({
                'ds': forecast_dates,
                'yhat': forecast.values
            })

            # Simulation-based confidence intervals
            try:
                simulations = model.simulate(
                    nsimulations=forecast_days,
                    repetitions=1000,
                    error='add'
                )
                forecast_df['yhat_lower'] = np.percentile(simulations, 2.5, axis=1)
                forecast_df['yhat_upper'] = np.percentile(simulations, 97.5, axis=1)
            except Exception:
                # Fallback: constant std_error bands
                residuals = model.resid
                std_error = np.std(residuals)
                forecast_df['yhat_lower'] = forecast_df['yhat'] - 1.96 * std_error
                forecast_df['yhat_upper'] = forecast_df['yhat'] + 1.96 * std_error

            # Apply bank holidays
            if model_data['apply_holidays'] and model_data['country_code']:
                holiday_dates = self.get_bank_holidays(
                    model_data['country_code'],
                    forecast_dates.min().year,
                    forecast_dates.max().year
                )

                is_holiday = forecast_df['ds'].isin(holiday_dates)
                forecast_df.loc[is_holiday, 'yhat'] = 0
                forecast_df.loc[is_holiday, 'yhat_lower'] = 0
                forecast_df.loc[is_holiday, 'yhat_upper'] = 0

            # Apply monthly volume distribution
            if channel in self.monthly_volumes:
                forecast_df = self._apply_monthly_distribution(forecast_df, channel)

            # Ensure no negative values
            forecast_df['yhat'] = forecast_df['yhat'].clip(lower=0)
            forecast_df['yhat_lower'] = forecast_df['yhat_lower'].clip(lower=0)
            forecast_df['yhat_upper'] = forecast_df['yhat_upper'].clip(lower=0)

            self.forecasts[channel] = forecast_df

            return forecast_df, "Forecast generated successfully"
        except Exception as e:
            return None, f"Error generating forecast: {str(e)}"

    def _apply_monthly_distribution(self, forecast, channel):
        """Distribute monthly target volumes across days"""
        monthly_targets = self.monthly_volumes[channel]

        forecast['month'] = forecast['ds'].dt.strftime('%Y-%m')

        for month_str, target_volume in monthly_targets.items():
            month_mask = forecast['month'] == month_str
            month_forecast = forecast[month_mask].copy()

            if len(month_forecast) == 0:
                continue

            current_total = month_forecast['yhat'].sum()

            if current_total > 0:
                scale_factor = target_volume / current_total
                forecast.loc[month_mask, 'yhat'] = month_forecast['yhat'] * scale_factor
                forecast.loc[month_mask, 'yhat_lower'] = month_forecast['yhat_lower'] * scale_factor
                forecast.loc[month_mask, 'yhat_upper'] = month_forecast['yhat_upper'] * scale_factor

        forecast = forecast.drop('month', axis=1)
        return forecast

    def blend_actuals_with_forecast(self, channel, actuals_df=None):
        """Blend actual data with forecast"""
        if actuals_df is not None and len(actuals_df) > 0:
            last_actual_date = actuals_df['Date'].max()

            forecast, msg = self.generate_forecast(channel, months_ahead=15, start_date=last_actual_date)

            if forecast is None:
                return None

            actuals_formatted = actuals_df.rename(columns={'Date': 'ds', 'Volume': 'yhat'})
            actuals_formatted['is_actual'] = True

            forecast['is_actual'] = False
            forecast_filtered = forecast[forecast['ds'] > last_actual_date]

            combined = pd.concat([
                actuals_formatted[['ds', 'yhat', 'is_actual']],
                forecast_filtered[['ds', 'yhat', 'yhat_lower', 'yhat_upper', 'is_actual']]
            ], ignore_index=True)

            return combined
        else:
            if channel in self.forecasts:
                forecast = self.forecasts[channel].copy()
                forecast['is_actual'] = False
                return forecast
            return None

    def get_weekly_aggregates(self, channel, year=None):
        """Get weekly aggregated volumes"""
        channel_data = self.historical_data[self.historical_data['Channel'] == channel].copy()

        if year is not None:
            channel_data = channel_data[channel_data['Date'].dt.year == year]

        channel_data['Week'] = channel_data['Date'].dt.isocalendar().week
        channel_data['Year'] = channel_data['Date'].dt.year

        weekly = channel_data.groupby(['Year', 'Week'])['Volume'].sum().reset_index()

        return weekly

    def compare_weeks(self, channel, week_numbers, years=[2024, 2025, 2026]):
        """Compare specific weeks across different years"""
        comparison_data = []

        for year in years:
            weekly_data = self.get_weekly_aggregates(channel, year)

            for week in week_numbers:
                week_data = weekly_data[weekly_data['Week'] == week]
                if not week_data.empty:
                    comparison_data.append({
                        'Year': year,
                        'Week': week,
                        'Volume': week_data['Volume'].values[0]
                    })

        return pd.DataFrame(comparison_data)

    def calculate_accuracy_metrics(self, channel, actual_df):
        """Calculate forecast accuracy metrics"""
        if channel not in self.forecasts:
            return None

        forecast = self.forecasts[channel]

        merged = actual_df.merge(forecast[['ds', 'yhat']], left_on='Date', right_on='ds', how='inner')

        if len(merged) == 0:
            return None

        actual = merged['Volume']
        predicted = merged['yhat']

        mape = np.mean(np.abs((actual - predicted) / actual)) * 100
        rmse = np.sqrt(np.mean((actual - predicted) ** 2))
        mae = np.mean(np.abs(actual - predicted))

        return {'MAPE': mape, 'RMSE': rmse, 'MAE': mae, 'Sample_Size': len(merged)}

    def get_seasonality_insights(self, channel):
        """Extract seasonality components"""
        if channel not in self.models:
            return None

        ts = self.models[channel]['ts']

        try:
            decomposition = seasonal_decompose(ts, model='additive', period=7, extrapolate_trend='freq')

            components = {
                'weekly': pd.DataFrame({'ds': decomposition.seasonal.index, 'weekly': decomposition.seasonal.values}),
                'trend': pd.DataFrame({'ds': decomposition.trend.index, 'trend': decomposition.trend.values}),
                'yearly': None
            }

            return components
        except:
            try:
                trend = pd.DataFrame({'ds': ts.index, 'trend': ts.rolling(window=7, center=True).mean().values})
                return {'weekly': None, 'trend': trend, 'yearly': None}
            except:
                return None

    def get_available_countries(self):
        """Get list of available countries for bank holidays"""
        return {
            'US': 'United States', 'GB': 'United Kingdom', 'FR': 'France', 'DE': 'Germany',
            'ES': 'Spain', 'IT': 'Italy', 'MA': 'Morocco', 'CA': 'Canada', 'AU': 'Australia',
            'JP': 'Japan', 'CN': 'China', 'IN': 'India', 'BR': 'Brazil', 'MX': 'Mexico',
            'NL': 'Netherlands', 'BE': 'Belgium', 'CH': 'Switzerland', 'AT': 'Austria',
            'SE': 'Sweden', 'NO': 'Norway', 'DK': 'Denmark', 'FI': 'Finland', 'PL': 'Poland',
            'PT': 'Portugal', 'IE': 'Ireland', 'NZ': 'New Zealand', 'SG': 'Singapore',
            'AE': 'United Arab Emirates', 'SA': 'Saudi Arabia', 'ZA': 'South Africa', 'EG': 'Egypt',
        }
