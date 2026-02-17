"""
Contact Volume Forecasting Engine - Enhanced Version with Prophet
Maximum accuracy forecasting with bank holidays and monthly volume distribution
"""

import pandas as pd
import numpy as np
from prophet import Prophet
from datetime import datetime, timedelta
import warnings
import holidays
warnings.filterwarnings('ignore')


class ContactForecaster:
    """
    Multi-channel contact volume forecasting with rolling 15-month predictions
    Uses Prophet for maximum accuracy
    """
    
    def __init__(self):
        self.models = {}
        self.forecasts = {}
        self.historical_data = None
        self.actuals_data = None
        self.bank_holiday_config = {}  # {channel: country_code}
        self.monthly_volumes = {}  # {channel: {month: volume}}
        
    def load_data(self, excel_path, sheet_name='Data'):
        """
        Load historical data from Excel
        Expected columns: Date, Channel, Volume
        """
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date')
            self.historical_data = df
            return True, "Data loaded successfully"
        except Exception as e:
            return False, f"Error loading data: {str(e)}"
    
    def configure_bank_holidays(self, channel, country_code):
        """
        Configure bank holidays for a specific channel
        country_code: ISO country code (e.g., 'US', 'GB', 'FR', 'MA')
        """
        self.bank_holiday_config[channel] = country_code
    
    def get_bank_holidays(self, country_code, start_year, end_year):
        """
        Get bank holidays for a country across multiple years
        """
        try:
            # Get holiday calendar for the country
            country_holidays = holidays.country_holidays(country_code)
            
            all_holidays = []
            for year in range(start_year, end_year + 1):
                # Iterate through all days in the year
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
            # Fallback: return common holidays
            return self._get_fallback_holidays(start_year, end_year)
    
    def _get_fallback_holidays(self, start_year, end_year):
        """
        Fallback common holidays if country not available
        """
        common_holidays = []
        for year in range(start_year, end_year + 1):
            common_holidays.extend([
                pd.Timestamp(f'{year}-01-01'),  # New Year
                pd.Timestamp(f'{year}-12-25'),  # Christmas
            ])
        return common_holidays
    
    def set_monthly_volumes(self, channel, monthly_data):
        """
        Set monthly target volumes from client
        monthly_data: dict like {'2026-03': 45000, '2026-04': 47000}
        or DataFrame with columns: Month, Volume
        """
        if isinstance(monthly_data, pd.DataFrame):
            monthly_dict = {}
            for _, row in monthly_data.iterrows():
                month_str = pd.to_datetime(row['Month']).strftime('%Y-%m')
                monthly_dict[month_str] = row['Volume']
            self.monthly_volumes[channel] = monthly_dict
        else:
            self.monthly_volumes[channel] = monthly_data
    
    def prepare_data_for_prophet(self, channel_data):
        """
        Convert data to Prophet format
        """
        prophet_df = pd.DataFrame({
            'ds': channel_data['Date'],
            'y': channel_data['Volume']
        })
        
        return prophet_df
    
    def train_model(self, channel, custom_seasonality=True):
        """
        Train Prophet model for a specific channel
        """
        channel_data = self.historical_data[
            self.historical_data['Channel'] == channel
        ].copy()
        
        if len(channel_data) < 30:
            return False, f"Insufficient data for {channel} (need at least 30 days)"
        
        # Check if bank holidays should be applied
        apply_holidays = channel in self.bank_holiday_config
        country_code = self.bank_holiday_config.get(channel)
        
        # Prepare data
        prophet_df = self.prepare_data_for_prophet(channel_data)
        
        # Create holidays dataframe for Prophet if configured
        holidays_df = None
        if apply_holidays and country_code:
            try:
                start_year = prophet_df['ds'].min().year
                end_year = prophet_df['ds'].max().year + 3  # Include future years
                holiday_dates = self.get_bank_holidays(country_code, start_year, end_year)
                
                holidays_df = pd.DataFrame({
                    'holiday': 'bank_holiday',
                    'ds': holiday_dates,
                    'lower_window': 0,
                    'upper_window': 0
                })
            except Exception as e:
                print(f"Warning: Could not load holidays for {country_code}: {e}")
        
        # Initialize Prophet with optimized settings
        try:
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=True,
                daily_seasonality=False,
                seasonality_mode='multiplicative',
                changepoint_prior_scale=0.05,
                interval_width=0.95,
                holidays=holidays_df
            )
            
            # Add monthly seasonality for better accuracy
            if custom_seasonality:
                model.add_seasonality(
                    name='monthly',
                    period=30.5,
                    fourier_order=5
                )
            
            # Fit the model
            model.fit(prophet_df)
            
            self.models[channel] = {
                'model': model,
                'apply_holidays': apply_holidays,
                'country_code': country_code
            }
            
            return True, f"Model trained for {channel}"
        except Exception as e:
            return False, f"Error training model for {channel}: {str(e)}"
    
    def generate_forecast(self, channel, months_ahead=15, start_date=None):
        """
        Generate rolling 15-month forecast from start_date
        Applies bank holidays and monthly volume distribution if configured
        """
        if channel not in self.models:
            return None, f"Model not trained for {channel}"
        
        model_info = self.models[channel]
        model = model_info['model']
        
        # Determine start date
        if start_date is None:
            channel_data = self.historical_data[
                self.historical_data['Channel'] == channel
            ]
            start_date = channel_data['Date'].max()
        
        # Create future dataframe
        future_dates = pd.date_range(
            start=start_date + timedelta(days=1),
            periods=months_ahead * 30,
            freq='D'
        )
        
        future_df = pd.DataFrame({'ds': future_dates})
        
        # Generate base forecast
        forecast = model.predict(future_df)
        
        # Apply bank holidays (zero out if configured)
        if model_info['apply_holidays'] and model_info['country_code']:
            holiday_dates = self.get_bank_holidays(
                model_info['country_code'],
                future_dates.min().year,
                future_dates.max().year
            )
            
            is_holiday = forecast['ds'].isin(holiday_dates)
            forecast.loc[is_holiday, 'yhat'] = 0
            forecast.loc[is_holiday, 'yhat_lower'] = 0
            forecast.loc[is_holiday, 'yhat_upper'] = 0
        
        # Apply monthly volume distribution if provided
        if channel in self.monthly_volumes:
            forecast = self._apply_monthly_distribution(forecast, channel)
        
        # Ensure no negative values
        forecast['yhat'] = forecast['yhat'].clip(lower=0)
        forecast['yhat_lower'] = forecast['yhat_lower'].clip(lower=0)
        forecast['yhat_upper'] = forecast['yhat_upper'].clip(lower=0)
        
        self.forecasts[channel] = forecast
        
        return forecast, "Forecast generated successfully"
    
    def _apply_monthly_distribution(self, forecast, channel):
        """
        Distribute monthly target volumes across days while maintaining patterns
        """
        monthly_targets = self.monthly_volumes[channel]
        
        # Add month column
        forecast['month'] = forecast['ds'].dt.strftime('%Y-%m')
        
        for month_str, target_volume in monthly_targets.items():
            # Get forecasts for this month
            month_mask = forecast['month'] == month_str
            month_forecast = forecast[month_mask].copy()
            
            if len(month_forecast) == 0:
                continue
            
            # Calculate current total and ratio
            current_total = month_forecast['yhat'].sum()
            
            if current_total > 0:
                # Calculate scaling factor
                scale_factor = target_volume / current_total
                
                # Scale all days proportionally
                forecast.loc[month_mask, 'yhat'] = month_forecast['yhat'] * scale_factor
                forecast.loc[month_mask, 'yhat_lower'] = month_forecast['yhat_lower'] * scale_factor
                forecast.loc[month_mask, 'yhat_upper'] = month_forecast['yhat_upper'] * scale_factor
            else:
                # If current total is 0 (all holidays), distribute evenly to non-zero days
                non_zero_mask = month_mask & (forecast['yhat'] > 0)
                non_zero_count = non_zero_mask.sum()
                if non_zero_count > 0:
                    daily_average = target_volume / non_zero_count
                    forecast.loc[non_zero_mask, 'yhat'] = daily_average
        
        forecast = forecast.drop('month', axis=1)
        return forecast
    
    def blend_actuals_with_forecast(self, channel, actuals_df=None):
        """
        Blend actual data with forecast, recalculating from the last actual date
        """
        if actuals_df is not None and len(actuals_df) > 0:
            last_actual_date = actuals_df['Date'].max()
            
            forecast, msg = self.generate_forecast(
                channel, 
                months_ahead=15, 
                start_date=last_actual_date
            )
            
            if forecast is None:
                return None
            
            actuals_formatted = actuals_df.rename(columns={
                'Date': 'ds',
                'Volume': 'yhat'
            })
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
        """
        Get weekly aggregated volumes for comparison
        """
        channel_data = self.historical_data[
            self.historical_data['Channel'] == channel
        ].copy()
        
        if year is not None:
            channel_data = channel_data[channel_data['Date'].dt.year == year]
        
        channel_data['Week'] = channel_data['Date'].dt.isocalendar().week
        channel_data['Year'] = channel_data['Date'].dt.year
        
        weekly = channel_data.groupby(['Year', 'Week'])['Volume'].sum().reset_index()
        
        return weekly
    
    def compare_weeks(self, channel, week_numbers, years=[2024, 2025, 2026]):
        """
        Compare specific weeks across different years
        """
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
        """
        Calculate forecast accuracy metrics (MAPE, RMSE, MAE)
        """
        if channel not in self.forecasts:
            return None
        
        forecast = self.forecasts[channel]
        
        merged = actual_df.merge(
            forecast[['ds', 'yhat']],
            left_on='Date',
            right_on='ds',
            how='inner'
        )
        
        if len(merged) == 0:
            return None
        
        actual = merged['Volume']
        predicted = merged['yhat']
        
        mape = np.mean(np.abs((actual - predicted) / actual)) * 100
        rmse = np.sqrt(np.mean((actual - predicted) ** 2))
        mae = np.mean(np.abs(actual - predicted))
        
        metrics = {
            'MAPE': mape,
            'RMSE': rmse,
            'MAE': mae,
            'Sample_Size': len(merged)
        }
        
        return metrics
    
    def get_seasonality_insights(self, channel):
        """
        Extract seasonality components from the Prophet model
        """
        if channel not in self.models:
            return None
        
        model = self.models[channel]['model']
        
        # Generate dates for analysis
        dates = pd.date_range(
            start=datetime.now() - timedelta(days=365),
            end=datetime.now(),
            freq='D'
        )
        
        df = pd.DataFrame({'ds': dates})
        forecast = model.predict(df)
        
        components = {
            'weekly': forecast[['ds', 'weekly']].copy() if 'weekly' in forecast.columns else None,
            'yearly': forecast[['ds', 'yearly']].copy() if 'yearly' in forecast.columns else None,
            'trend': forecast[['ds', 'trend']].copy() if 'trend' in forecast.columns else None
        }
        
        return components
    
    def get_available_countries(self):
        """
        Get list of available countries for bank holidays
        """
        return {
            'US': 'United States',
            'GB': 'United Kingdom',
            'FR': 'France',
            'DE': 'Germany',
            'ES': 'Spain',
            'IT': 'Italy',
            'MA': 'Morocco',
            'CA': 'Canada',
            'AU': 'Australia',
            'JP': 'Japan',
            'CN': 'China',
            'IN': 'India',
            'BR': 'Brazil',
            'MX': 'Mexico',
            'NL': 'Netherlands',
            'BE': 'Belgium',
            'CH': 'Switzerland',
            'AT': 'Austria',
            'SE': 'Sweden',
            'NO': 'Norway',
            'DK': 'Denmark',
            'FI': 'Finland',
            'PL': 'Poland',
            'PT': 'Portugal',
            'IE': 'Ireland',
            'NZ': 'New Zealand',
            'SG': 'Singapore',
            'AE': 'United Arab Emirates',
            'SA': 'Saudi Arabia',
            'ZA': 'South Africa',
            'EG': 'Egypt',
        }
