"""
Excel parsing and validation for uploaded historical data files.
"""
from io import BytesIO

import pandas as pd


REQUIRED_COLUMNS = {"Date", "Channel", "Volume"}


class DataValidationError(Exception):
    pass


def parse_excel(content: bytes) -> pd.DataFrame:
    """Parse uploaded Excel bytes. Returns a clean DataFrame (Date, Channel, Volume)."""
    try:
        df = pd.read_excel(BytesIO(content), sheet_name="Data")
    except Exception:
        try:
            df = pd.read_excel(BytesIO(content))
        except Exception as e:
            raise DataValidationError(f"Cannot read Excel file: {e}") from e

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise DataValidationError(
            f"Missing required columns: {sorted(missing)}. "
            f"Found: {list(df.columns)}"
        )

    df = df[["Date", "Channel", "Volume"]].copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")

    bad_dates = df["Date"].isna().sum()
    bad_vols = df["Volume"].isna().sum()
    if bad_dates > 0 or bad_vols > 0:
        raise DataValidationError(
            f"Data quality issues: {bad_dates} unparseable dates, "
            f"{bad_vols} non-numeric volumes."
        )

    df = df.sort_values("Date").reset_index(drop=True)
    return df


def extract_metadata(df: pd.DataFrame) -> dict:
    """Extract summary statistics from a clean DataFrame."""
    return {
        "row_count": len(df),
        "channels": sorted(df["Channel"].unique().tolist()),
        "date_min": df["Date"].min().date(),
        "date_max": df["Date"].max().date(),
    }
