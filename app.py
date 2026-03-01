"""
Contact Volume Forecasting Dashboard
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from forecasting_engine import ContactForecaster

st.set_page_config(
    page_title="Contact Volume Forecasting",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Theme CSS
# ---------------------------------------------------------------------------

def get_css(theme: str) -> str:
    dark = theme == "dark"

    bg        = "#0F172A" if dark else "#F8FAFC"
    surface   = "#1E293B" if dark else "#FFFFFF"
    surface2  = "#162032" if dark else "#F1F5F9"
    border    = "#2D3E52" if dark else "#E2E8F0"
    text      = "#E2E8F0" if dark else "#1E293B"
    text2     = "#94A3B8" if dark else "#64748B"
    accent    = "#3B82F6" if dark else "#2563EB"
    shadow    = "rgba(0,0,0,0.35)" if dark else "rgba(0,0,0,0.07)"

    return f"""
<style>
/* ── Base ── */
html, body, [data-testid="stAppViewContainer"], .stApp {{
    background-color: {bg} !important;
    color: {text} !important;
}}
[data-testid="stHeader"] {{
    background-color: {bg} !important;
    border-bottom: 1px solid {border};
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] > div:first-child {{
    background-color: {surface} !important;
    border-right: 1px solid {border};
}}
[data-testid="stSidebar"] * {{
    color: {text} !important;
}}
[data-testid="stSidebar"] label {{
    color: {text2} !important;
}}

/* ── Main block ── */
[data-testid="block-container"],
[data-testid="stMainBlockContainer"] {{
    background-color: {bg} !important;
}}
.main .block-container {{
    padding-top: 1rem;
}}

/* ── Text ── */
p, li, span, div {{
    color: {text};
}}
h1, h2, h3, h4, h5, h6 {{
    color: {text} !important;
}}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span {{
    color: {text} !important;
}}
label {{
    color: {text2} !important;
    font-size: 0.85rem;
}}

/* ── Metric cards ── */
[data-testid="metric-container"] {{
    background-color: {surface} !important;
    border: 1px solid {border} !important;
    border-radius: 12px !important;
    padding: 1rem 1.25rem !important;
    box-shadow: 0 1px 4px {shadow} !important;
}}
[data-testid="stMetricValue"] {{
    color: {text} !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
}}
[data-testid="stMetricLabel"] {{
    color: {text2} !important;
    font-size: 0.8rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
[data-testid="stMetricDelta"] {{
    font-size: 0.85rem !important;
}}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {{
    background-color: {surface2} !important;
    border-radius: 10px;
    padding: 3px;
    gap: 2px;
    border: 1px solid {border};
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 7px !important;
    padding: 6px 18px !important;
    color: {text2} !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    background-color: transparent !important;
    border: none !important;
}}
.stTabs [aria-selected="true"] {{
    background-color: {surface} !important;
    color: {accent} !important;
    box-shadow: 0 1px 3px {shadow} !important;
}}
.stTabs [data-baseweb="tab-highlight"] {{
    display: none;
}}
.stTabs [data-baseweb="tab-border"] {{
    display: none;
}}

/* ── Buttons ── */
.stButton > button {{
    background-color: {surface} !important;
    color: {text} !important;
    border: 1px solid {border} !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.15s ease;
}}
.stButton > button:hover {{
    border-color: {accent} !important;
    color: {accent} !important;
}}
.stButton > button[kind="primary"] {{
    background-color: {accent} !important;
    color: #FFFFFF !important;
    border-color: {accent} !important;
}}
.stButton > button[kind="primary"]:hover {{
    filter: brightness(1.1);
}}

/* ── Inputs ── */
[data-baseweb="select"] > div,
[data-baseweb="input"],
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
.stTextInput input,
.stNumberInput input {{
    background-color: {surface} !important;
    border-color: {border} !important;
    color: {text} !important;
    border-radius: 8px !important;
}}
[data-baseweb="select"] svg {{
    fill: {text2} !important;
}}
[data-baseweb="popover"] [data-baseweb="menu"] {{
    background-color: {surface} !important;
    border: 1px solid {border} !important;
}}
[data-baseweb="popover"] li {{
    background-color: {surface} !important;
    color: {text} !important;
}}
[data-baseweb="popover"] li:hover {{
    background-color: {surface2} !important;
}}

/* ── File uploader ── */
[data-testid="stFileUploaderDropzone"] {{
    background-color: {surface2} !important;
    border: 2px dashed {border} !important;
    border-radius: 10px !important;
}}

/* ── Expanders ── */
[data-testid="stExpander"] {{
    background-color: {surface} !important;
    border: 1px solid {border} !important;
    border-radius: 10px !important;
}}
[data-testid="stExpander"] summary {{
    color: {text} !important;
}}
details > summary {{
    color: {text} !important;
    font-weight: 500;
}}

/* ── Alerts / info boxes ── */
[data-testid="stAlert"] {{
    background-color: {surface} !important;
    border-radius: 10px !important;
    border: 1px solid {border} !important;
}}
[data-testid="stAlert"] p {{
    color: {text} !important;
}}

/* ── Progress bar ── */
.stProgress > div > div {{
    background-color: {accent} !important;
}}

/* ── Checkbox ── */
[data-testid="stCheckbox"] p {{
    color: {text} !important;
}}

/* ── Divider ── */
hr {{
    border-color: {border} !important;
    opacity: 0.6;
}}

/* ── DataFrames ── */
[data-testid="stDataFrame"] {{
    border: 1px solid {border} !important;
    border-radius: 10px !important;
}}

/* ── Custom classes ── */
.header-banner {{
    background: linear-gradient(135deg, #1D4ED8 0%, #6D28D9 100%);
    padding: 1.75rem 2rem;
    border-radius: 14px;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 24px rgba(29,78,216,0.3);
}}
.header-banner h1 {{
    color: white !important;
    font-size: 1.85rem !important;
    font-weight: 700 !important;
    margin: 0 0 0.3rem 0 !important;
}}
.header-banner p {{
    color: rgba(255,255,255,0.82) !important;
    font-size: 0.95rem !important;
    margin: 0 !important;
}}
.section-label {{
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: {text2};
    margin: 1.5rem 0 0.5rem 0;
    padding-bottom: 0.25rem;
    border-bottom: 1px solid {border};
}}
.accuracy-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 0.4rem 0.9rem;
    font-size: 0.8rem;
    color: {text2};
    margin-bottom: 0.75rem;
}}
.feature-badge {{
    display: inline-block;
    padding: 0.2rem 0.65rem;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    margin: 0.15rem;
}}
.badge-holidays {{ background: #D97706; color: white; }}
.badge-volumes  {{ background: #047857; color: white; }}
</style>
"""


CHART_COLORS = ['#2563EB', '#7C3AED', '#059669', '#F59E0B', '#EF4444', '#EC4899']
CHART_FONT   = dict(family="Inter, system-ui, sans-serif", size=12)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if 'forecaster' not in st.session_state:
    st.session_state.forecaster               = ContactForecaster()
    st.session_state.data_loaded              = False
    st.session_state.models_trained           = False
    st.session_state.bank_holidays_configured = {}
    st.session_state.monthly_volumes_configured = {}

if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    theme = st.session_state.theme
    st.markdown(get_css(theme), unsafe_allow_html=True)
    plotly_tpl = 'plotly_dark' if theme == 'dark' else 'plotly_white'

    # Header banner
    st.markdown("""
    <div class="header-banner">
        <h1>📊 Contact Volume Forecasting</h1>
        <p>AI-powered 15-month rolling forecast · seasonal adjustment · bank holidays · client targets</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        col_l, col_r = st.columns([1, 1])
        with col_l:
            if theme == 'light':
                if st.button("🌙 Dark", use_container_width=True):
                    st.session_state.theme = 'dark'
            else:
                if st.button("☀️ Light", use_container_width=True):
                    st.session_state.theme = 'light'
        with col_r:
            st.markdown(f"<p style='font-size:0.75rem;color:#94A3B8;margin-top:0.45rem'>{'Dark mode' if theme=='dark' else 'Light mode'}</p>",
                        unsafe_allow_html=True)

        # ── 1. Data upload ───────────────────────────────────────────────────
        st.markdown('<div class="section-label">1 · Historical Data</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Excel file (Date, Channel, Volume)",
            type=['xlsx', 'xls'],
            label_visibility="collapsed",
        )
        if uploaded_file:
            tmp = f"/tmp/{uploaded_file.name}"
            with open(tmp, "wb") as f:
                f.write(uploaded_file.getbuffer())
            ok, msg = st.session_state.forecaster.load_data(tmp)
            if ok:
                st.success(msg)
                st.session_state.data_loaded = True
            else:
                st.error(msg)

        if not st.session_state.data_loaded:
            st.markdown('<div class="section-label">2 · Configure</div>', unsafe_allow_html=True)
            st.caption("Upload data first")
        else:
            channels = st.session_state.forecaster.historical_data['Channel'].unique()
            df_hist  = st.session_state.forecaster.historical_data
            date_min = df_hist['Date'].min().strftime('%d %b %Y')
            date_max = df_hist['Date'].max().strftime('%d %b %Y')
            st.info(f"**{len(channels)} channels** · {date_min} → {date_max}")

            # ── 2. Configure ─────────────────────────────────────────────────
            st.markdown('<div class="section-label">2 · Configure (optional)</div>',
                        unsafe_allow_html=True)

            with st.expander("🏖️ Bank Holidays", expanded=False):
                countries   = st.session_state.forecaster.get_available_countries()
                country_code = st.selectbox(
                    "Country",
                    options=list(countries.keys()),
                    format_func=lambda x: f"{countries[x]} ({x})",
                    key="country_selector",
                )
                for ch in channels:
                    if st.checkbox(ch, value=ch in st.session_state.bank_holidays_configured,
                                   key=f"hol_{ch}"):
                        st.session_state.bank_holidays_configured[ch] = country_code
                        st.session_state.forecaster.configure_bank_holidays(ch, country_code)
                    elif ch in st.session_state.bank_holidays_configured:
                        del st.session_state.bank_holidays_configured[ch]
                if st.session_state.bank_holidays_configured:
                    st.caption(f"✅ {len(st.session_state.bank_holidays_configured)} channel(s)")

            with st.expander("📅 Monthly Volume Targets", expanded=False):
                sel_ch = st.selectbox("Channel", channels, key="mv_ch")
                c1, c2 = st.columns(2)
                with c1:
                    start_m = st.date_input("Start", datetime(2026, 3, 1), key="mv_start")
                with c2:
                    n_months = st.number_input("Months", 1, 15, 3, key="mv_n")
                mv = {}
                for i in range(int(n_months)):
                    md_date = start_m + pd.DateOffset(months=i)
                    v = st.number_input(md_date.strftime('%b %Y'), 0, step=1000,
                                        key=f"mv_{sel_ch}_{i}")
                    if v > 0:
                        mv[md_date.strftime('%Y-%m')] = v
                if st.button("💾 Save", key="mv_save", use_container_width=True):
                    if mv:
                        st.session_state.forecaster.set_monthly_volumes(sel_ch, mv)
                        st.session_state.monthly_volumes_configured[sel_ch] = mv
                        st.success(f"Saved {len(mv)} month(s)")
                    else:
                        st.warning("No volumes entered")
                if st.session_state.monthly_volumes_configured:
                    for ch, data in st.session_state.monthly_volumes_configured.items():
                        st.caption(f"✅ {ch}: {len(data)} months")

            # ── 3. Train ──────────────────────────────────────────────────────
            st.markdown('<div class="section-label">3 · Train Models</div>',
                        unsafe_allow_html=True)

            active = []
            if st.session_state.bank_holidays_configured:
                active.append('<span class="feature-badge badge-holidays">🏖️ Holidays</span>')
            if st.session_state.monthly_volumes_configured:
                active.append('<span class="feature-badge badge-volumes">📅 Targets</span>')
            if active:
                st.markdown(" ".join(active), unsafe_allow_html=True)

            if st.button("🚀 Train All Models", type="primary", use_container_width=True):
                with st.spinner("Training models…"):
                    bar = st.progress(0)
                    ok_n, err_n, errors = 0, 0, []
                    for i, ch in enumerate(channels):
                        ts, tm = st.session_state.forecaster.train_model(ch)
                        if ts:
                            fd, fm = st.session_state.forecaster.generate_forecast(ch, 15)
                            if fd is not None:
                                ok_n += 1
                            else:
                                err_n += 1; errors.append(f"{ch}: {fm}")
                        else:
                            err_n += 1; errors.append(f"{ch}: {tm}")
                        bar.progress((i + 1) / len(channels))
                    st.session_state.models_trained = True
                if ok_n:
                    st.success(f"✅ {ok_n}/{len(channels)} channels ready")
                for e in errors:
                    st.error(e)

            # ── 4. Actuals ────────────────────────────────────────────────────
            if st.session_state.models_trained:
                st.markdown('<div class="section-label">4 · Blend Actuals (optional)</div>',
                            unsafe_allow_html=True)
                actuals_f = st.file_uploader("2026 actuals (Date, Channel, Volume)",
                                             type=['xlsx', 'xls'], key="actuals_up",
                                             label_visibility="collapsed")
                if actuals_f:
                    st.info("Uploaded — use the Forecasts tab to view blended view")

    # ── Main area ─────────────────────────────────────────────────────────────
    if not st.session_state.data_loaded:
        _show_welcome()
    elif not st.session_state.models_trained:
        _show_data_preview(plotly_tpl)
    else:
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Forecasts",
            "📊 Week Comparison",
            "🔍 Seasonality",
            "🏖️ Bank Holidays",
            "📋 Summary & Export",
        ])
        with tab1: show_forecasts(plotly_tpl)
        with tab2: show_week_comparison(plotly_tpl)
        with tab3: show_seasonality_analysis(plotly_tpl)
        with tab4: show_bank_holidays_view()
        with tab5: show_summary_report(plotly_tpl)


# ---------------------------------------------------------------------------
# Welcome / data preview helpers
# ---------------------------------------------------------------------------

def _show_welcome():
    st.info("👈 Upload your historical Excel file in the sidebar to get started.")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("Expected format")
        st.dataframe(pd.DataFrame({
            'Date':    pd.date_range('2024-01-01', 5, freq='D'),
            'Channel': ['Calls', 'Emails', 'Chats', 'Messages', 'Calls'],
            'Volume':  [1250, 850, 430, 320, 1180],
        }), use_container_width=True)
    with c2:
        st.subheader("What this app does")
        st.markdown("""
- **Two-stage forecasting**: weekly Holt-Winters + monthly seasonal adjustment
- Automatically selects best model via AIC (8 configurations tested)
- Damped trend to prevent runaway long-range extrapolation
- Simulation-based 95% confidence intervals
- Bank holiday zeroing per channel/country
- Client monthly volume target distribution
- Backtest view to validate model accuracy
""")


def _show_data_preview(plotly_tpl):
    forecaster = st.session_state.forecaster
    df = forecaster.historical_data

    st.info("👈 Configure options and train models in the sidebar.")

    channels = df['Channel'].unique()
    c1, c2, c3, c4 = st.columns(4)
    for i, col in enumerate([c1, c2, c3, c4]):
        if i < len(channels):
            ch = channels[i]
            avg = df[df['Channel'] == ch]['Volume'].mean()
            col.metric(ch, f"{avg:,.0f}", "avg daily")

    st.subheader("Monthly volumes by channel")
    df2 = df.copy()
    df2['Month'] = df2['Date'].dt.to_period('M').dt.to_timestamp()
    monthly = df2.groupby(['Month', 'Channel'])['Volume'].sum().reset_index()
    fig = px.line(monthly, x='Month', y='Volume', color='Channel',
                  color_discrete_sequence=CHART_COLORS,
                  title="Historical Monthly Volumes")
    fig.update_layout(height=400, template=plotly_tpl, font=CHART_FONT,
                      hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Raw data preview"):
        st.dataframe(df.head(50), use_container_width=True)


# ---------------------------------------------------------------------------
# Tab 1 – Forecasts
# ---------------------------------------------------------------------------

def show_forecasts(plotly_tpl):
    forecaster = st.session_state.forecaster

    if not forecaster.models:
        st.warning("No models trained yet.")
        return
    if not forecaster.forecasts:
        st.warning("No forecasts available — please retrain models.")
        return

    channels = list(forecaster.models.keys())
    sel = st.selectbox("Channel", channels, key="fc_ch")

    if sel not in forecaster.forecasts or forecaster.forecasts[sel] is None:
        st.error(f"No forecast for {sel}. Please retrain.")
        return

    historical = forecaster.historical_data[
        forecaster.historical_data['Channel'] == sel
    ].copy()
    forecast = forecaster.forecasts[sel].copy()

    # ── Model info bar ────────────────────────────────────────────────────────
    md = forecaster.models.get(sel, {})
    cfg  = md.get('config', ('?', '?', '?'))
    aic  = md.get('aic')
    bt   = forecaster.get_backtest_metrics(sel, holdout_days=60)
    mape_str = f"Backtest MAPE: {bt['MAPE']:.1f}%" if bt else "Backtest: n/a"
    cfg_str  = f"trend={cfg[0]}, seasonal={cfg[1]}, damped={cfg[2]}"
    aic_str  = f"AIC: {aic:.0f}" if aic else ""

    feat_html = ""
    if sel in st.session_state.bank_holidays_configured:
        feat_html += f'<span class="feature-badge badge-holidays">🏖️ {st.session_state.bank_holidays_configured[sel]}</span>'
    if sel in st.session_state.monthly_volumes_configured:
        n = len(st.session_state.monthly_volumes_configured[sel])
        feat_html += f'<span class="feature-badge badge-volumes">📅 {n}mo targets</span>'

    st.markdown(
        f'<div class="accuracy-badge">'
        f'<b>{cfg_str}</b>&nbsp;·&nbsp;{aic_str}&nbsp;·&nbsp;<b>{mape_str}</b>'
        f'</div>{feat_html}',
        unsafe_allow_html=True,
    )

    # ── KPI row ───────────────────────────────────────────────────────────────
    hist_avg = historical['Volume'].mean()
    fc_avg   = forecast['yhat'].mean()
    change   = (fc_avg - hist_avg) / hist_avg * 100
    fc_total = forecast['yhat'].sum()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Avg Historical / day", f"{hist_avg:,.0f}")
    k2.metric("Avg Forecast / day",   f"{fc_avg:,.0f}", f"{change:+.1f}%")
    k3.metric("15-Month Total",        f"{fc_total:,.0f}")
    k4.metric("Forecast horizon",
              f"{(forecast['ds'].max() - forecast['ds'].min()).days} days")

    # ── Daily forecast chart ──────────────────────────────────────────────────
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=historical['Date'], y=historical['Volume'],
        name='Historical', line=dict(color='#2563EB', width=1.5),
    ))
    fig.add_trace(go.Scatter(
        x=forecast['ds'], y=forecast['yhat'],
        name='Forecast', line=dict(color='#F59E0B', width=2, dash='dash'),
    ))
    fig.add_trace(go.Scatter(
        x=pd.concat([forecast['ds'], forecast['ds'][::-1]]),
        y=pd.concat([forecast['yhat_upper'], forecast['yhat_lower'][::-1]]),
        fill='toself', fillcolor='rgba(245,158,11,0.12)',
        line=dict(color='rgba(0,0,0,0)'),
        name='95% CI', showlegend=True,
    ))
    if sel in st.session_state.bank_holidays_configured:
        hm = forecast['yhat'] == 0
        if hm.any():
            fig.add_trace(go.Scatter(
                x=forecast.loc[hm, 'ds'],
                y=[forecast['yhat'].replace(0, np.nan).max() * 0.04] * hm.sum(),
                mode='markers', name='Bank Holiday',
                marker=dict(color='#EF4444', size=7, symbol='diamond'),
            ))
    fig.update_layout(
        title=f"{sel} — Daily Forecast (15 months)",
        xaxis_title="Date", yaxis_title="Volume",
        hovermode='x unified', height=440,
        template=plotly_tpl, font=CHART_FONT,
        legend=dict(orientation='h', y=-0.18),
        margin=dict(b=60),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Monthly aggregates chart ──────────────────────────────────────────────
    st.subheader("Monthly volume overview")

    hist_m = (historical
              .assign(Month=historical['Date'].dt.to_period('M'))
              .groupby('Month')['Volume'].sum()
              .reset_index())
    hist_m['Month_ts'] = hist_m['Month'].dt.to_timestamp()
    hist_m['type'] = 'Historical'

    fc_m = (forecast
            .assign(Month=forecast['ds'].dt.to_period('M'))
            .groupby('Month')['yhat'].sum()
            .reset_index())
    fc_m_lo = (forecast
               .assign(Month=forecast['ds'].dt.to_period('M'))
               .groupby('Month')['yhat_lower'].sum()
               .reset_index())
    fc_m_hi = (forecast
               .assign(Month=forecast['ds'].dt.to_period('M'))
               .groupby('Month')['yhat_upper'].sum()
               .reset_index())
    fc_m['Month_ts']    = fc_m['Month'].dt.to_timestamp()
    fc_m_lo['Month_ts'] = fc_m_lo['Month'].dt.to_timestamp()
    fc_m_hi['Month_ts'] = fc_m_hi['Month'].dt.to_timestamp()

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=hist_m['Month_ts'], y=hist_m['Volume'],
        name='Historical', marker_color='#2563EB', opacity=0.85,
    ))
    fig2.add_trace(go.Bar(
        x=fc_m['Month_ts'], y=fc_m['yhat'],
        name='Forecast', marker_color='#F59E0B', opacity=0.85,
        error_y=dict(
            type='data',
            array=(fc_m_hi['yhat_upper'] - fc_m['yhat']).values,
            arrayminus=(fc_m['yhat'] - fc_m_lo['yhat_lower']).values,
            visible=True,
            color='rgba(245,158,11,0.5)',
        ),
    ))
    fig2.update_layout(
        barmode='overlay',
        title=f"{sel} — Monthly Totals (historical + forecast)",
        xaxis_title="Month", yaxis_title="Monthly Volume",
        height=380, template=plotly_tpl, font=CHART_FONT,
        hovermode='x unified',
        legend=dict(orientation='h', y=-0.2),
        margin=dict(b=60),
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ── Back-test accuracy ────────────────────────────────────────────────────
    with st.expander("🔬 Model accuracy — last 60-day backtest", expanded=False):
        bt_df = forecaster.backtest(sel, holdout_days=60)
        if bt_df is not None and len(bt_df):
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(
                x=bt_df['ds'], y=bt_df['actual'],
                name='Actual', line=dict(color='#2563EB', width=2),
            ))
            fig3.add_trace(go.Scatter(
                x=bt_df['ds'], y=bt_df['predicted'],
                name='Model', line=dict(color='#F59E0B', width=2, dash='dot'),
            ))
            fig3.update_layout(
                title="Actual vs Model (held-out test set)",
                xaxis_title="Date", yaxis_title="Volume",
                hovermode='x unified', height=320,
                template=plotly_tpl, font=CHART_FONT,
            )
            st.plotly_chart(fig3, use_container_width=True)

            mape = bt_df['error_pct'].mean()
            mae  = np.abs(bt_df['actual'] - bt_df['predicted']).mean()
            c1, c2, c3 = st.columns(3)
            c1.metric("MAPE",  f"{mape:.1f}%",  help="Mean Absolute % Error")
            c2.metric("MAE",   f"{mae:,.0f}",   help="Mean Absolute Error")
            c3.metric("Days tested", len(bt_df))
        else:
            st.info("Not enough data for backtest (need > 74 days).")

    # ── Forecast data table ────────────────────────────────────────────────────
    with st.expander("📊 Forecast data table"):
        disp = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
        disp.columns = ['Date', 'Forecast', 'Lower 95%', 'Upper 95%']
        disp['Date'] = disp['Date'].dt.date
        disp[['Forecast', 'Lower 95%', 'Upper 95%']] = disp[
            ['Forecast', 'Lower 95%', 'Upper 95%']
        ].round(0)
        if sel in st.session_state.monthly_volumes_configured:
            disp['Month'] = pd.to_datetime(disp['Date']).dt.strftime('%Y-%m')
            st.markdown("**Monthly totals (targets applied):**")
            st.dataframe(disp.groupby('Month')['Forecast'].sum().rename("Monthly Total"),
                         use_container_width=True)
            disp = disp.drop('Month', axis=1)
        st.dataframe(disp, use_container_width=True)


# ---------------------------------------------------------------------------
# Tab 2 – Week comparison
# ---------------------------------------------------------------------------

def show_week_comparison(plotly_tpl):
    st.header("Week Comparison Across Years")
    forecaster = st.session_state.forecaster
    channels   = list(forecaster.models.keys())

    c1, c2 = st.columns(2)
    with c1:
        sel = st.selectbox("Channel", channels, key="wc_ch")
    with c2:
        week_input = st.text_input("Week numbers (comma-separated)", "1,10,20,30,40,52")

    try:
        weeks = [int(w.strip()) for w in week_input.split(',')]
        df = forecaster.compare_weeks(sel, weeks, years=[2024, 2025])
        if df.empty:
            st.warning("No data for selected weeks.")
            return

        fig = px.bar(df, x='Week', y='Volume', color='Year', barmode='group',
                     title=f"{sel} — Weekly Volume Comparison",
                     color_discrete_sequence=CHART_COLORS)
        fig.update_layout(height=440, template=plotly_tpl, font=CHART_FONT)
        st.plotly_chart(fig, use_container_width=True)

        pivot = df.pivot(index='Week', columns='Year', values='Volume').fillna(0)
        if 2025 in pivot.columns and 2024 in pivot.columns:
            pivot['YoY %'] = ((pivot[2025] - pivot[2024]) / pivot[2024] * 100).round(1)
        st.dataframe(pivot, use_container_width=True)
    except ValueError:
        st.error("Enter valid week numbers 1–52 separated by commas.")


# ---------------------------------------------------------------------------
# Tab 3 – Seasonality
# ---------------------------------------------------------------------------

def show_seasonality_analysis(plotly_tpl):
    st.header("Seasonality Analysis")
    forecaster = st.session_state.forecaster
    channels   = list(forecaster.models.keys())
    sel        = st.selectbox("Channel", channels, key="sa_ch")

    # Show extracted monthly factors
    md = forecaster.models.get(sel, {})
    mf = md.get('monthly_factors')
    if mf:
        st.subheader("📆 Monthly seasonal factors (used in forecast)")
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        vals = [mf.get(m, 1.0) for m in range(1, 13)]
        colors = ['#EF4444' if v > 1.05 else '#2563EB' if v < 0.95 else '#94A3B8'
                  for v in vals]
        fig = go.Figure(data=[go.Bar(
            x=month_names, y=vals,
            marker_color=colors,
            text=[f"{v:.2f}" for v in vals],
            textposition='outside',
        )])
        fig.add_hline(y=1.0, line_dash='dot', line_color='#94A3B8',
                      annotation_text="Baseline (1.0)")
        fig.update_layout(
            title=f"{sel} — Monthly seasonal index (>1 = above average)",
            yaxis_title="Seasonal factor", height=380,
            template=plotly_tpl, font=CHART_FONT,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Weekly pattern
    comps = forecaster.get_seasonality_insights(sel)
    if comps and comps.get('weekly') is not None:
        st.subheader("📅 Weekly pattern")
        wd = comps['weekly'].copy()
        wd['dow'] = pd.to_datetime(wd['ds']).dt.day_name()
        avg = wd.groupby('dow')['weekly'].mean().reindex(
            ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
        fig2 = go.Figure(data=[go.Bar(
            x=avg.index, y=avg.values,
            marker_color=['#2563EB' if v >= 0 else '#EF4444' for v in avg.values],
        )])
        fig2.update_layout(
            title="Day-of-week seasonality effect",
            yaxis_title="Additive effect",
            height=320, template=plotly_tpl, font=CHART_FONT,
        )
        st.plotly_chart(fig2, use_container_width=True)


# ---------------------------------------------------------------------------
# Tab 4 – Bank holidays
# ---------------------------------------------------------------------------

def show_bank_holidays_view():
    st.header("🏖️ Bank Holidays")
    if not st.session_state.bank_holidays_configured:
        st.info("No bank holidays configured. Set them up in the sidebar.")
        return

    forecaster   = st.session_state.forecaster
    countries    = forecaster.get_available_countries()
    current_year = datetime.now().year

    for ch, cc in st.session_state.bank_holidays_configured.items():
        st.success(f"✅ **{ch}** — {countries.get(cc, cc)} holidays applied")

    c1, c2 = st.columns(2)
    with c1:
        sel_cc = st.selectbox(
            "Country", list(set(st.session_state.bank_holidays_configured.values())),
            format_func=lambda x: countries.get(x, x))
    with c2:
        sel_yr = st.selectbox("Year", [current_year, current_year+1, current_year+2])

    h_list = forecaster.get_bank_holidays(sel_cc, sel_yr, sel_yr)
    h_df   = pd.DataFrame({'Date': [h for h in h_list if h.year == sel_yr]})
    h_df['Day of Week'] = pd.to_datetime(h_df['Date']).dt.day_name()
    h_df['Date'] = pd.to_datetime(h_df['Date']).dt.date

    st.subheader(f"Holidays in {sel_yr}")
    st.dataframe(h_df, use_container_width=True)
    st.caption(f"{len(h_df)} holiday(s) → forecast volume set to zero on these days.")


# ---------------------------------------------------------------------------
# Tab 5 – Summary & export
# ---------------------------------------------------------------------------

def show_summary_report(plotly_tpl):
    st.header("Summary Report")
    forecaster = st.session_state.forecaster
    channels   = list(forecaster.models.keys())

    if not forecaster.forecasts:
        st.info("Train models to see the summary.")
        return

    # ── Summary table ─────────────────────────────────────────────────────────
    rows = []
    for ch in channels:
        fc = forecaster.forecasts.get(ch)
        if fc is None:
            continue
        hist = forecaster.historical_data[
            forecaster.historical_data['Channel'] == ch]
        ha   = hist['Volume'].mean()
        fa   = fc['yhat'].mean()
        tot  = fc['yhat'].sum()
        chg  = (fa - ha) / ha * 100
        mf   = forecaster.models.get(ch, {}).get('monthly_factors', {})
        peak = max(mf, key=mf.get) if mf else '—'
        trough = min(mf, key=mf.get) if mf else '—'
        import calendar
        peak_name   = calendar.month_abbr[peak]   if isinstance(peak, int)   else '—'
        trough_name = calendar.month_abbr[trough] if isinstance(trough, int) else '—'
        badges = []
        if ch in st.session_state.bank_holidays_configured: badges.append("🏖️")
        if ch in st.session_state.monthly_volumes_configured: badges.append("📅")
        rows.append({
            'Channel':          f"{ch} {''.join(badges)}",
            'Hist. avg/day':    f"{ha:,.0f}",
            'Forecast avg/day': f"{fa:,.0f}",
            'Change':           f"{chg:+.1f}%",
            '15M Total':        f"{tot:,.0f}",
            'Peak month':       peak_name,
            'Trough month':     trough_name,
        })

    if not rows:
        st.warning("No forecast data.")
        return

    summary_df = pd.DataFrame(rows)
    st.dataframe(summary_df, use_container_width=True)
    st.caption("🏖️ = holidays applied  |  📅 = monthly targets applied")

    # ── Channel comparison bar chart ──────────────────────────────────────────
    st.subheader("15-Month forecast by channel")
    comp = [{'Channel': ch,
             'Total': forecaster.forecasts[ch]['yhat'].sum()}
            for ch in channels if ch in forecaster.forecasts and forecaster.forecasts[ch] is not None]
    if comp:
        fig = px.bar(pd.DataFrame(comp), x='Channel', y='Total',
                     color='Channel', color_discrete_sequence=CHART_COLORS,
                     title="Total forecast volume per channel")
        fig.update_layout(height=380, template=plotly_tpl, font=CHART_FONT, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # ── Export ────────────────────────────────────────────────────────────────
    st.subheader("Export")
    e1, e2 = st.columns(2)

    with e1:
        if st.button("📥 All Forecasts (Excel)", use_container_width=True):
            out = "/tmp/forecasts_export.xlsx"
            with pd.ExcelWriter(out, engine='openpyxl') as writer:
                for ch in channels:
                    fc = forecaster.forecasts.get(ch)
                    if fc is None:
                        continue
                    ex = fc[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
                    ex.columns = ['Date', 'Forecast', 'Lower 95%', 'Upper 95%']
                    ex.to_excel(writer, sheet_name=ch[:31], index=False)
            with open(out, 'rb') as f:
                st.download_button("⬇️ Download",  f.read(),
                    file_name=f"forecasts_{datetime.now():%Y%m%d}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with e2:
        if st.button("📊 Summary (Excel)", use_container_width=True):
            out = "/tmp/summary.xlsx"
            summary_df.to_excel(out, index=False)
            with open(out, 'rb') as f:
                st.download_button("⬇️ Download", f.read(),
                    file_name=f"summary_{datetime.now():%Y%m%d}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


if __name__ == "__main__":
    main()
