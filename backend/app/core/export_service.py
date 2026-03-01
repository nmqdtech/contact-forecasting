"""
Build Excel export bytes from in-memory data.
"""
from io import BytesIO

import pandas as pd


def build_forecasts_excel(channel_forecasts: dict[str, pd.DataFrame]) -> bytes:
    """
    channel_forecasts: {channel_name: DataFrame(date, yhat, yhat_lower, yhat_upper)}
    Returns Excel file as bytes with one sheet per channel.
    """
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for channel, df in channel_forecasts.items():
            out = df.rename(
                columns={
                    "date": "Date",
                    "yhat": "Forecast",
                    "yhat_lower": "Lower 95%",
                    "yhat_upper": "Upper 95%",
                }
            )
            sheet_name = channel[:31]  # Excel sheet name limit
            out.to_excel(writer, sheet_name=sheet_name, index=False)
    return buf.getvalue()


def build_summary_excel(summary_rows: list[dict]) -> bytes:
    """summary_rows: list of dicts matching SummaryRow schema fields."""
    buf = BytesIO()
    df = pd.DataFrame(summary_rows)
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Summary", index=False)
    return buf.getvalue()
