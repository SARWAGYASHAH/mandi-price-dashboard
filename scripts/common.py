"""Shared paths and data helpers for the mandi analytics pipeline."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
CLEANED_DIR = ROOT / "data" / "cleaned"
OUTPUT_DIR = ROOT / "data" / "outputs"
INSIGHTS_DIR = ROOT / "insights"
VISUALS_DIR = ROOT / "visuals"
POWERBI_DIR = ROOT / "powerbi"
DOCS_DIR = ROOT / "docs"

TARGET_COMMODITIES = ("Onion", "Tomato", "Potato", "Wheat", "Rice")
STATE_ALIASES = {
    "Chattisgarh": "Chhattisgarh",
    "Gao": "Goa",
    "Jammu & Kashmir": "Jammu and Kashmir",
    "Jammu And Kashmir": "Jammu and Kashmir",
    "Orissa": "Odisha",
    "Tamilnadu": "Tamil Nadu",
    "Uttrakhand": "Uttarakhand",
}
REQUIRED_COLUMNS = (
    "state",
    "district",
    "market",
    "commodity",
    "variety",
    "grade",
    "arrival_date",
    "min_price",
    "max_price",
    "modal_price",
)

COLUMN_ALIASES = {
    "state": "state",
    "district": "district",
    "district_name": "district",
    "market": "market",
    "market_name": "market",
    "commodity": "commodity",
    "variety": "variety",
    "grade": "grade",
    "arrival_date": "arrival_date",
    "price_date": "arrival_date",
    "date": "arrival_date",
    "min_price": "min_price",
    "minimum_price": "min_price",
    "max_price": "max_price",
    "maximum_price": "max_price",
    "modal_price": "modal_price",
    "mode_price": "modal_price",
}


def ensure_directories() -> None:
    """Create every generated-output directory used by the project."""
    for path in (
        CLEANED_DIR,
        OUTPUT_DIR,
        INSIGHTS_DIR,
        VISUALS_DIR,
        POWERBI_DIR / "dashboard_screenshots",
        DOCS_DIR,
        ROOT / "sql" / "query_results",
    ):
        path.mkdir(parents=True, exist_ok=True)


def snake_case(value: str) -> str:
    """Convert a source column name to lowercase snake_case."""
    value = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
    value = re.sub(r"_+", "_", value)
    return value.strip("_").lower()


def standardize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize source headers and apply known schema aliases."""
    normalized = {column: snake_case(str(column)) for column in frame.columns}
    frame = frame.rename(columns=normalized)
    frame = frame.rename(
        columns={column: COLUMN_ALIASES.get(column, column) for column in frame.columns}
    )

    duplicates = frame.columns[frame.columns.duplicated()].tolist()
    if duplicates:
        raise ValueError(f"Duplicate columns after standardization: {duplicates}")

    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    return frame.loc[:, list(REQUIRED_COLUMNS)].copy()


def read_cleaned_data(parse_dates: bool = True) -> pd.DataFrame:
    """Read the canonical cleaned dataset with a clear failure message."""
    path = CLEANED_DIR / "mandi_cleaned_master.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} does not exist. Run `python scripts/data_cleaning.py` first."
        )
    return pd.read_csv(path, parse_dates=["arrival_date"] if parse_dates else None)


def currency(value: float) -> str:
    """Format a rupee-denominated numeric value for reports."""
    return f"INR {value:,.0f}"
