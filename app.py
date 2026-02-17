"""
Interactive Contact Volume Forecasting Dashboard - Enhanced Version
Features:
- Bank holiday configuration per channel
- Monthly volume input from client
- Smart daily distribution
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
from forecasting_engine import ContactForecaster

# Page configuration
st.set_page_config(
    page_title="Contact Volume Forecasting System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .feature-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        font-weight: 600;
        margin: 0.25rem;
    }
    .badge-holidays {
        background-color: #ff7f0e;
        color: white;
    }
    .badge-volumes {
        background-color: #2ca02c;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'forecaster' not in st.session_state:
    st.session_state.forecaster = ContactForecaster()
    st.session_state.data_loaded = False
    st.session_state.models_trained = False
    st.session_state.bank_holidays_configured = {}
    st.session_state.monthly_volumes_configured = {}

def main():
    st.markdown('<p class="main-header">📊 Contact Volume Forecasting System</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-Powered 15-Month Rolling Forecast with Bank Holidays & Client Volume Targets</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 Configuration")
        
        st.subheader("1️⃣ Upload Historical Data")
        uploaded_file = st.file_uploader(
            "Upload Excel file with historical data",
            type=['xlsx', 'xls'],
            help="Required columns: Date, Channel, Volume"
        )
        
        if uploaded_file is not None:
            temp_path = f"/tmp/{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            success, msg = st.session_state.forecaster.load_data(temp_path)
            if success:
                st.success(msg)
                st.session_state.data_loaded = True
            else:
                st.error(msg)
        
        st.divider()
        
        if st.session_state.data_loaded:
            channels = st.session_state.forecaster.historical_data['Channel'].unique()
            st.info(f"✅ Detected {len(channels)} channels")
            
            # Bank Holidays Configuration
            with st.expander("🏖️ **Bank Holidays Configuration**", expanded=False):
                st.markdown("**Configure which channels should respect bank holidays**")
                
                countries = st.session_state.forecaster.get_available_countries()
                
                st.markdown("##### Select Country")
                country_code = st.selectbox(
                    "Country for bank holidays",
                    options=list(countries.keys()),
                    format_func=lambda x: f"{countries[x]} ({x})",
                    key="country_selector"
                )
                
                st.markdown("##### Select Channels")
                st.markdown("*Choose channels that should have zero volume on bank holidays*")
                
                for channel in channels:
                    apply_holidays = st.checkbox(
                        f"{channel}",
                        value=channel in st.session_state.bank_holidays_configured,
                        key=f"holiday_{channel}"
                    )
                    
                    if apply_holidays:
                        st.session_state.bank_holidays_configured[channel] = country_code
                        st.session_state.forecaster.configure_bank_holidays(channel, country_code)
                    elif channel in st.session_state.bank_holidays_configured:
                        del st.session_state.bank_holidays_configured[channel]
                
                if st.session_state.bank_holidays_configured:
                    st.success(f"✅ {len(st.session_state.bank_holidays_configured)} channel(s) configured")
            
            # Monthly Volumes Configuration
            with st.expander("📅 **Monthly Volume Targets** (Optional)", expanded=False):
                st.markdown("**Provide monthly volumes from your client**")
                st.markdown("*These will override AI predictions and be distributed daily*")
                
                selected_channel = st.selectbox(
                    "Select Channel",
                    options=channels,
                    key="monthly_channel_selector"
                )
                
                st.markdown("##### Enter Monthly Volumes")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    start_month = st.date_input(
                        "Start Month",
                        value=datetime(2026, 3, 1),
                        key="start_month"
                    )
                
                with col2:
                    num_months = st.number_input(
                        "Number of Months",
                        min_value=1,
                        max_value=15,
                        value=3,
                        key="num_months"
                    )
                
                # Create input fields for each month
                monthly_data = {}
                st.markdown("**Monthly Volumes:**")
                
                for i in range(int(num_months)):
                    month_date = start_month + pd.DateOffset(months=i)
                    month_str = month_date.strftime('%Y-%m')
                    month_display = month_date.strftime('%B %Y')
                    
                    volume = st.number_input(
                        month_display,
                        min_value=0,
                        value=0,
                        step=1000,
                        key=f"monthly_vol_{selected_channel}_{i}"
                    )
                    
                    if volume > 0:
                        monthly_data[month_str] = volume
                
                if st.button("💾 Save Monthly Volumes", key="save_monthly"):
                    if monthly_data:
                        st.session_state.forecaster.set_monthly_volumes(selected_channel, monthly_data)
                        st.session_state.monthly_volumes_configured[selected_channel] = monthly_data
                        st.success(f"✅ Saved {len(monthly_data)} month(s) for {selected_channel}")
                    else:
                        st.warning("No volumes entered")
                
                # Show configured channels
                if st.session_state.monthly_volumes_configured:
                    st.markdown("**Configured Channels:**")
                    for ch, data in st.session_state.monthly_volumes_configured.items():
                        st.info(f"✅ {ch}: {len(data)} month(s)")
            
            st.divider()
            
            st.subheader("2️⃣ Train Models")
            
            # Show active features
            if st.session_state.bank_holidays_configured or st.session_state.monthly_volumes_configured:
                st.markdown("**Active Features:**")
                if st.session_state.bank_holidays_configured:
                    st.markdown('<span class="feature-badge badge-holidays">🏖️ Bank Holidays</span>', unsafe_allow_html=True)
                if st.session_state.monthly_volumes_configured:
                    st.markdown('<span class="feature-badge badge-volumes">📅 Monthly Targets</span>', unsafe_allow_html=True)
            
            if st.button("🚀 Train All Models", type="primary", use_container_width=True):
                with st.spinner("Training models... This may take a minute."):
                    progress_bar = st.progress(0)
                    for i, channel in enumerate(channels):
                        success, msg = st.session_state.forecaster.train_model(channel)
                        if success:
                            st.session_state.forecaster.generate_forecast(channel, months_ahead=15)
                        progress_bar.progress((i + 1) / len(channels))
                    
                    st.session_state.models_trained = True
                    st.success("✅ All models trained successfully!")
                    st.rerun()
        
        st.divider()
        
        if st.session_state.models_trained:
            st.subheader("3️⃣ Update with Actuals (Optional)")
            actuals_file = st.file_uploader(
                "Upload 2026 actuals to recalculate forecast",
                type=['xlsx', 'xls'],
                help="Required columns: Date, Channel, Volume"
            )
            
            if actuals_file is not None:
                st.info("Actuals uploaded - forecast will be recalculated")
    
    # Main content area
    if not st.session_state.data_loaded:
        st.info("👈 Please upload your historical data in the sidebar to get started")
        
        st.subheader("📋 Expected Data Format")
        example_df = pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=5, freq='D'),
            'Channel': ['Calls', 'Emails', 'Chats', 'Messages', 'Calls'],
            'Volume': [1250, 850, 430, 320, 1180]
        })
        st.dataframe(example_df, use_container_width=True)
        
    elif not st.session_state.models_trained:
        st.info("👈 Configure features and train models in the sidebar")
        
        st.subheader("📊 Data Preview")
        st.dataframe(
            st.session_state.forecaster.historical_data.head(20),
            use_container_width=True
        )
        
    else:
        # Create tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Forecasts", 
            "📊 Week Comparison", 
            "🔍 Seasonality Analysis",
            "🏖️ Bank Holidays View",
            "📋 Summary Report"
        ])
        
        with tab1:
            show_forecasts()
        
        with tab2:
            show_week_comparison()
        
        with tab3:
            show_seasonality_analysis()
        
        with tab4:
            show_bank_holidays_view()
        
        with tab5:
            show_summary_report()


def show_forecasts():
    """Display forecast visualizations"""
    st.header("15-Month Rolling Forecast")
    
    forecaster = st.session_state.forecaster
    channels = list(forecaster.models.keys())
    
    selected_channel = st.selectbox("Select Channel", channels)
    
    if selected_channel:
        # Show active features for this channel
        features = []
        if selected_channel in st.session_state.bank_holidays_configured:
            country = st.session_state.bank_holidays_configured[selected_channel]
            features.append(f"🏖️ Bank Holidays ({country})")
        if selected_channel in st.session_state.monthly_volumes_configured:
            num_months = len(st.session_state.monthly_volumes_configured[selected_channel])
            features.append(f"📅 Monthly Targets ({num_months} months)")
        
        if features:
            st.info("**Active Features:** " + " | ".join(features))
        
        # Get data
        historical = forecaster.historical_data[
            forecaster.historical_data['Channel'] == selected_channel
        ].copy()
        
        forecast = forecaster.forecasts[selected_channel]
        
        # Create plot
        fig = go.Figure()
        
        # Historical
        fig.add_trace(go.Scatter(
            x=historical['Date'],
            y=historical['Volume'],
            mode='lines',
            name='Historical',
            line=dict(color='#1f77b4', width=2)
        ))
        
        # Forecast
        fig.add_trace(go.Scatter(
            x=forecast['ds'],
            y=forecast['yhat'],
            mode='lines',
            name='Forecast',
            line=dict(color='#ff7f0e', width=2, dash='dash')
        ))
        
        # Confidence interval
        fig.add_trace(go.Scatter(
            x=forecast['ds'].tolist() + forecast['ds'].tolist()[::-1],
            y=forecast['yhat_upper'].tolist() + forecast['yhat_lower'].tolist()[::-1],
            fill='toself',
            fillcolor='rgba(255,127,14,0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            name='95% Confidence',
            showlegend=True
        ))
        
        # Highlight bank holidays if configured
        if selected_channel in st.session_state.bank_holidays_configured:
            holiday_mask = forecast['yhat'] == 0
            if holiday_mask.any():
                fig.add_trace(go.Scatter(
                    x=forecast[holiday_mask]['ds'],
                    y=[forecast['yhat'].max() * 0.05] * holiday_mask.sum(),
                    mode='markers',
                    name='Bank Holidays',
                    marker=dict(color='red', size=8, symbol='diamond'),
                    showlegend=True
                ))
        
        fig.update_layout(
            title=f"{selected_channel} - 15 Month Forecast",
            xaxis_title="Date",
            yaxis_title="Volume",
            hovermode='x unified',
            height=500,
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_historical = historical['Volume'].mean()
            st.metric("Avg Historical Volume", f"{avg_historical:,.0f}")
        
        with col2:
            avg_forecast = forecast['yhat'].mean()
            st.metric("Avg Forecast Volume", f"{avg_forecast:,.0f}")
        
        with col3:
            change = ((avg_forecast - avg_historical) / avg_historical) * 100
            st.metric("Expected Change", f"{change:+.1f}%")
        
        with col4:
            total_forecast = forecast['yhat'].sum()
            st.metric("Total 15-Month Forecast", f"{total_forecast:,.0f}")
        
        # Data table
        with st.expander("📊 View Detailed Forecast Data"):
            forecast_display = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
            forecast_display.columns = ['Date', 'Forecast', 'Lower Bound', 'Upper Bound']
            forecast_display['Date'] = pd.to_datetime(forecast_display['Date']).dt.date
            
            # Add monthly volumes if configured
            if selected_channel in st.session_state.monthly_volumes_configured:
                forecast_display['Month'] = pd.to_datetime(forecast_display['Date']).dt.strftime('%Y-%m')
                monthly_totals = forecast_display.groupby('Month')['Forecast'].sum()
                st.markdown("**Monthly Totals (with client targets applied):**")
                st.dataframe(monthly_totals, use_container_width=True)
            
            st.dataframe(forecast_display, use_container_width=True)


def show_week_comparison():
    """Week comparison view"""
    st.header("Week Comparison Across Years")
    
    forecaster = st.session_state.forecaster
    channels = list(forecaster.models.keys())
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_channel = st.selectbox("Select Channel", channels, key="week_channel")
    
    with col2:
        week_input = st.text_input(
            "Enter week numbers (comma-separated)",
            value="1,10,20,30,40,52"
        )
    
    try:
        week_numbers = [int(w.strip()) for w in week_input.split(',')]
        
        comparison_df = forecaster.compare_weeks(
            selected_channel,
            week_numbers,
            years=[2024, 2025]
        )
        
        if not comparison_df.empty:
            fig = px.bar(
                comparison_df,
                x='Week',
                y='Volume',
                color='Year',
                barmode='group',
                title=f"{selected_channel} - Weekly Volume Comparison"
            )
            
            fig.update_layout(height=400, template='plotly_white')
            st.plotly_chart(fig, use_container_width=True)
            
            # Show table
            pivot_table = comparison_df.pivot(
                index='Week',
                columns='Year',
                values='Volume'
            ).fillna(0)
            
            if 2025 in pivot_table.columns and 2024 in pivot_table.columns:
                pivot_table['YoY Change %'] = (
                    (pivot_table[2025] - pivot_table[2024]) / pivot_table[2024] * 100
                ).round(1)
            
            st.dataframe(pivot_table, use_container_width=True)
        else:
            st.warning("No data available for selected weeks")
            
    except ValueError:
        st.error("Please enter valid week numbers (1-52) separated by commas")


def show_seasonality_analysis():
    """Seasonality analysis view"""
    st.header("Seasonality Analysis")
    
    forecaster = st.session_state.forecaster
    channels = list(forecaster.models.keys())
    
    selected_channel = st.selectbox("Select Channel", channels, key="season_channel")
    
    components = forecaster.get_seasonality_insights(selected_channel)
    
    if components:
        if components['weekly'] is not None:
            st.subheader("📅 Weekly Seasonality Pattern")
            
            weekly_df = components['weekly'].copy()
            weekly_df['day_of_week'] = pd.to_datetime(weekly_df['ds']).dt.day_name()
            
            weekly_avg = weekly_df.groupby('day_of_week')['weekly'].mean().reindex([
                'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
            ])
            
            fig = go.Figure(data=[go.Bar(x=weekly_avg.index, y=weekly_avg.values)])
            fig.update_layout(
                title="Average Weekly Pattern",
                xaxis_title="Day of Week",
                yaxis_title="Seasonality Effect",
                height=300,
                template='plotly_white'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        if components['yearly'] is not None:
            st.subheader("📆 Yearly Seasonality Pattern")
            
            yearly_df = components['yearly'].copy()
            yearly_df['month'] = pd.to_datetime(yearly_df['ds']).dt.month
            
            monthly_avg = yearly_df.groupby('month')['yearly'].mean()
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            
            fig = go.Figure(data=[go.Scatter(x=month_names, y=monthly_avg.values, mode='lines+markers')])
            fig.update_layout(
                title="Average Monthly Pattern",
                xaxis_title="Month",
                yaxis_title="Seasonality Effect",
                height=300,
                template='plotly_white'
            )
            st.plotly_chart(fig, use_container_width=True)


def show_bank_holidays_view():
    """Bank holidays calendar view"""
    st.header("🏖️ Bank Holidays Calendar")
    
    if not st.session_state.bank_holidays_configured:
        st.info("No bank holidays configured. Configure in the sidebar to see the calendar.")
        return
    
    forecaster = st.session_state.forecaster
    
    # Show configured channels
    st.subheader("Configured Channels")
    for channel, country in st.session_state.bank_holidays_configured.items():
        countries = forecaster.get_available_countries()
        st.success(f"✅ **{channel}**: {countries.get(country, country)} bank holidays applied")
    
    # Get holidays for current and next year
    current_year = datetime.now().year
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_country = st.selectbox(
            "Select Country to View",
            options=list(set(st.session_state.bank_holidays_configured.values())),
            format_func=lambda x: forecaster.get_available_countries().get(x, x)
        )
    
    with col2:
        selected_year = st.selectbox(
            "Select Year",
            options=[current_year, current_year + 1, current_year + 2],
            index=0
        )
    
    # Get holidays
    holidays_list = forecaster.get_bank_holidays(selected_country, selected_year, selected_year)
    holidays_df = pd.DataFrame({
        'Date': [pd.to_datetime(h) for h in holidays_list if h.year == selected_year],
    })
    holidays_df['Day of Week'] = holidays_df['Date'].dt.day_name()
    holidays_df['Date'] = holidays_df['Date'].dt.date
    
    st.subheader(f"Bank Holidays in {selected_year}")
    st.dataframe(holidays_df, use_container_width=True)
    
    # Show impact
    st.subheader("Impact on Forecasts")
    st.info(f"For channels with {forecaster.get_available_countries()[selected_country]} bank holidays, forecasts will be **zero** on these {len(holidays_df)} days, with volumes redistributed to other days.")


def show_summary_report():
    """Summary report view"""
    st.header("📋 Automated Summary Report")
    
    forecaster = st.session_state.forecaster
    channels = list(forecaster.models.keys())
    
    st.subheader("🎯 Forecast Overview")
    
    summary_data = []
    
    for channel in channels:
        historical = forecaster.historical_data[
            forecaster.historical_data['Channel'] == channel
        ]
        forecast = forecaster.forecasts[channel]
        
        hist_avg = historical['Volume'].mean()
        forecast_avg = forecast['yhat'].mean()
        forecast_total = forecast['yhat'].sum()
        change_pct = ((forecast_avg - hist_avg) / hist_avg) * 100
        
        # Add feature indicators
        features = []
        if channel in st.session_state.bank_holidays_configured:
            features.append("🏖️")
        if channel in st.session_state.monthly_volumes_configured:
            features.append("📅")
        
        feature_str = " ".join(features) if features else ""
        
        summary_data.append({
            'Channel': f"{channel} {feature_str}",
            'Historical Avg Daily': f"{hist_avg:,.0f}",
            'Forecast Avg Daily': f"{forecast_avg:,.0f}",
            'Change %': f"{change_pct:+.1f}%",
            '15-Month Total': f"{forecast_total:,.0f}"
        })
    
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, use_container_width=True)
    
    # Legend
    st.caption("🏖️ = Bank holidays applied | 📅 = Monthly targets applied")
    
    # Visual comparison
    st.subheader("📊 Channel Comparison")
    
    comparison_data = []
    for channel in channels:
        forecast = forecaster.forecasts[channel]
        total = forecast['yhat'].sum()
        comparison_data.append({'Channel': channel, 'Total Forecast Volume': total})
    
    comparison_df = pd.DataFrame(comparison_data)
    
    fig = px.bar(
        comparison_df,
        x='Channel',
        y='Total Forecast Volume',
        title="15-Month Forecast by Channel",
        color='Channel'
    )
    
    fig.update_layout(height=400, template='plotly_white', showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    
    # Export
    st.subheader("💾 Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Download All Forecasts (Excel)", use_container_width=True):
            output_path = "/tmp/forecasts_export.xlsx"
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                for channel in channels:
                    forecast = forecaster.forecasts[channel][['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
                    forecast.columns = ['Date', 'Forecast', 'Lower Bound', 'Upper Bound']
                    forecast.to_excel(writer, sheet_name=channel, index=False)
            
            with open(output_path, 'rb') as f:
                st.download_button(
                    "⬇️ Download",
                    f.read(),
                    file_name=f"contact_forecasts_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    
    with col2:
        if st.button("📊 Download Summary Report (Excel)", use_container_width=True):
            output_path = "/tmp/summary_report.xlsx"
            summary_df.to_excel(output_path, index=False)
            
            with open(output_path, 'rb') as f:
                st.download_button(
                    "⬇️ Download",
                    f.read(),
                    file_name=f"forecast_summary_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )


if __name__ == "__main__":
    main()
