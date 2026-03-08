"""
File parsing and validation for uploaded historical data files.
Supports Excel (.xlsx/.xls) and CSV formats.
Supports daily (Date/Channel/Volume) and hourly (Date/Time/Channel/Volume) layouts.
Optional columns: AHT (seconds), Junior_Ratio (0.0–1.0) or Junior_Count (normalised to ratio).
"""
from io import BytesIO

import numpy as np
import pandas as pd


REQUIRED_DAILY_COLUMNS = {"Date", "Channel", "Volume"}
REQUIRED_HOURLY_COLUMNS = {"Date", "Time", "Channel", "Volume"}

# Optional column aliases (case-normalised at parse time)
_AHT_ALIASES = {"aht", "handle_time", "avg_handle_time", "average_handle_time"}
_JUNIOR_RATIO_ALIASES = {"junior_ratio", "jr_ratio"}
_JUNIOR_COUNT_ALIASES = {"junior_count", "jr_count", "junior", "juniors"}


class DataValidationError(Exception):
    pass


def _find_col(columns: list[str], aliases: set[str]) -> str | None:
    """Return the first column whose lowercase name matches any alias."""
    col_map = {c.lower(): c for c in columns}
    for alias in aliases:
        if alias in col_map:
            return col_map[alias]
    return None


def parse_file(content: bytes, filename: str) -> pd.DataFrame:
    """Parse uploaded file bytes. Returns a clean DataFrame."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "csv":
        try:
            df = pd.read_csv(BytesIO(content))
        except Exception as e:
            raise DataValidationError(f"Cannot read CSV file: {e}") from e
    else:
        try:
            df = pd.read_excel(BytesIO(content), sheet_name="Data")
        except Exception:
            try:
                df = pd.read_excel(BytesIO(content))
            except Exception as e:
                raise DataValidationError(f"Cannot read Excel file: {e}") from e

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
    aht_col = _find_col(list(df.columns), _AHT_ALIASES)
    jr_ratio_col = _find_col(list(df.columns), _JUNIOR_RATIO_ALIASES)
    jr_count_col = _find_col(list(df.columns), _JUNIOR_COUNT_ALIASES)

    keep = ["Date", "Channel", "Volume"]
    if aht_col:
        keep.append(aht_col)
    if jr_ratio_col:
        keep.append(jr_ratio_col)
    elif jr_count_col:
        keep.append(jr_count_col)

    df = df[keep].copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")

    if aht_col:
        df[aht_col] = pd.to_numeric(df[aht_col], errors="coerce")

    bad_dates = df["Date"].isna().sum()
    bad_vols = df["Volume"].isna().sum()
    if bad_dates > 0 or bad_vols > 0:
        raise DataValidationError(
            f"Data quality issues: {bad_dates} unparseable dates, "
            f"{bad_vols} non-numeric volumes."
        )

    # Build aggregation spec
    agg: dict = {"Volume": "sum"}
    if aht_col:
        # Volume-weighted average AHT
        df["_vol_x_aht"] = df["Volume"] * df[aht_col].fillna(0)
        agg["_vol_x_aht"] = "sum"

    if jr_ratio_col:
        df.rename(columns={jr_ratio_col: "Junior_Ratio"}, inplace=True)
        agg["Junior_Ratio"] = "mean"
    elif jr_count_col:
        df.rename(columns={jr_count_col: "Junior_Count"}, inplace=True)
        agg["Junior_Count"] = "sum"

    grouped = df.groupby(["Channel", "Date"], as_index=False).agg(agg)

    if aht_col:
        total_vol = grouped["Volume"].replace(0, np.nan)
        grouped["AHT"] = grouped["_vol_x_aht"] / total_vol
        grouped.drop(columns=["_vol_x_aht"], inplace=True)

    if jr_count_col and "Junior_Count" in grouped.columns:
        # Normalise: ratio = count / max count per channel (proxy for total agents)
        max_by_channel = grouped.groupby("Channel")["Junior_Count"].transform("max")
        grouped["Junior_Ratio"] = (grouped["Junior_Count"] / max_by_channel.replace(0, np.nan)).clip(0, 1)
        grouped.drop(columns=["Junior_Count"], inplace=True)

    return grouped.sort_values("Date").reset_index(drop=True)


def _parse_hourly(df: pd.DataFrame) -> pd.DataFrame:
    aht_col = _find_col(list(df.columns), _AHT_ALIASES)
    jr_ratio_col = _find_col(list(df.columns), _JUNIOR_RATIO_ALIASES)
    jr_count_col = _find_col(list(df.columns), _JUNIOR_COUNT_ALIASES)

    keep = ["Date", "Time", "Channel", "Volume"]
    if aht_col:
        keep.append(aht_col)
    if jr_ratio_col:
        keep.append(jr_ratio_col)
    elif jr_count_col:
        keep.append(jr_count_col)

    df = df[keep].copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")

    if aht_col:
        df[aht_col] = pd.to_numeric(df[aht_col], errors="coerce")

    bad_dates = df["Date"].isna().sum()
    bad_vols = df["Volume"].isna().sum()
    if bad_dates > 0 or bad_vols > 0:
        raise DataValidationError(
            f"Data quality issues: {bad_dates} unparseable dates, "
            f"{bad_vols} non-numeric volumes."
        )

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
    df.drop(columns=["Time"], inplace=True)

    # Rename optional cols before groupby
    if aht_col:
        df.rename(columns={aht_col: "AHT"}, inplace=True)
    if jr_ratio_col:
        df.rename(columns={jr_ratio_col: "Junior_Ratio"}, inplace=True)
    elif jr_count_col:
        df.rename(columns={jr_count_col: "Junior_Count"}, inplace=True)

    group_cols = ["Channel", "Date", "Hour"]
    agg: dict = {"Volume": "sum"}

    if "AHT" in df.columns:
        df["_vol_x_aht"] = df["Volume"] * df["AHT"].fillna(0)
        agg["_vol_x_aht"] = "sum"

    if "Junior_Ratio" in df.columns:
        agg["Junior_Ratio"] = "mean"
    elif "Junior_Count" in df.columns:
        agg["Junior_Count"] = "sum"

    grouped = df.groupby(group_cols, as_index=False).agg(agg)

    if "AHT" in df.columns:
        total_vol = grouped["Volume"].replace(0, np.nan)
        grouped["AHT"] = grouped["_vol_x_aht"] / total_vol
        grouped.drop(columns=["_vol_x_aht"], inplace=True)

    if "Junior_Count" in grouped.columns:
        max_by_channel = grouped.groupby("Channel")["Junior_Count"].transform("max")
        grouped["Junior_Ratio"] = (grouped["Junior_Count"] / max_by_channel.replace(0, np.nan)).clip(0, 1)
        grouped.drop(columns=["Junior_Count"], inplace=True)

    return grouped.sort_values(["Date", "Hour"]).reset_index(drop=True)


def extract_metadata(df: pd.DataFrame) -> dict:
    """Extract summary statistics from a clean DataFrame."""
    is_hourly = "Hour" in df.columns
    has_aht = "AHT" in df.columns
    meta: dict = {
        "row_count": len(df),
        "channels": sorted(df["Channel"].unique().tolist()),
        "date_min": df["Date"].min().date(),
        "date_max": df["Date"].max().date(),
        "is_hourly": is_hourly,
        "has_aht": has_aht,
    }
    if is_hourly:
        meta["hour_min"] = int(df["Hour"].min())
        meta["hour_max"] = int(df["Hour"].max())
    return meta


# Legacy alias
def parse_excel(content: bytes) -> pd.DataFrame:
    return parse_file(content, "file.xlsx")
