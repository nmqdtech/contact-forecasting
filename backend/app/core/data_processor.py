"""
File parsing and validation for uploaded historical data files.
Supports Excel (.xlsx/.xls) and CSV formats.
Supports daily (Date/Channel/Volume) and hourly (Date/Time/Channel/Volume) layouts.
"""
from io import BytesIO

import pandas as pd


REQUIRED_DAILY_COLUMNS = {"Date", "Channel", "Volume"}
REQUIRED_HOURLY_COLUMNS = {"Date", "Time", "Channel", "Volume"}


class DataValidationError(Exception):
    pass


def parse_file(content: bytes, filename: str) -> pd.DataFrame:
    """Parse uploaded file bytes. Returns a clean DataFrame."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "csv":
        try:
            df = pd.read_csv(BytesIO(content))
        except Exception as e:
            raise DataValidationError(f"Cannot read CSV file: {e}") from e
    else:
        # Excel
        try:
            df = pd.read_excel(BytesIO(content), sheet_name="Data")
        except Exception:
            try:
                df = pd.read_excel(BytesIO(content))
            except Exception as e:
                raise DataValidationError(f"Cannot read Excel file: {e}") from e

    # Detect layout by checking for Time column
    if "Time" in df.columns:
        missing = REQUIRED_HOURLY_COLUMNS - set(df.columns)
        if missing:
            raise DataValidationError(
                f"Hourly format requires columns: {sorted(REQUIRED_HOURLY_COLUMNS)}. "
                f"Missing: {sorted(missing)}. Found: {list(df.columns)}"
            )
        return _parse_hourly(df)
    else:
        missing = REQUIRED_DAILY_COLUMNS - set(df.columns)
        if missing:
            raise DataValidationError(
                f"Missing required columns: {sorted(missing)}. "
                f"Found: {list(df.columns)}"
            )
        return _parse_daily(df)


def _parse_daily(df: pd.DataFrame) -> pd.DataFrame:
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

    df = (
        df.groupby(["Channel", "Date"], as_index=False)["Volume"]
        .sum()
    )
    df = df.sort_values("Date").reset_index(drop=True)
    return df


def _parse_hourly(df: pd.DataFrame) -> pd.DataFrame:
    df = df[["Date", "Time", "Channel", "Volume"]].copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")

    bad_dates = df["Date"].isna().sum()
    bad_vols = df["Volume"].isna().sum()
    if bad_dates > 0 or bad_vols > 0:
        raise DataValidationError(
            f"Data quality issues: {bad_dates} unparseable dates, "
            f"{bad_vols} non-numeric volumes."
        )

    # Parse Time column to integer hour (0-23)
    # Accept "HH:MM", "H:MM", or bare integer
    def _to_hour(val) -> int:
        if pd.isna(val):
            return 0
        s = str(val).strip()
        if ":" in s:
            try:
                return int(s.split(":")[0])
            except ValueError:
                return 0
        try:
            return int(float(s))
        except ValueError:
            return 0

    df["Hour"] = df["Time"].apply(_to_hour).clip(0, 23)
    df = df.drop(columns=["Time"])

    # Aggregate duplicates
    df = (
        df.groupby(["Channel", "Date", "Hour"], as_index=False)["Volume"]
        .sum()
    )
    df = df.sort_values(["Date", "Hour"]).reset_index(drop=True)
    return df


def extract_metadata(df: pd.DataFrame) -> dict:
    """Extract summary statistics from a clean DataFrame."""
    is_hourly = "Hour" in df.columns
    meta: dict = {
        "row_count": len(df),
        "channels": sorted(df["Channel"].unique().tolist()),
        "date_min": df["Date"].min().date(),
        "date_max": df["Date"].max().date(),
        "is_hourly": is_hourly,
    }
    if is_hourly:
        meta["hour_min"] = int(df["Hour"].min())
        meta["hour_max"] = int(df["Hour"].max())
    return meta


# Legacy alias kept for any remaining direct imports
def parse_excel(content: bytes) -> pd.DataFrame:
    return parse_file(content, "file.xlsx")
