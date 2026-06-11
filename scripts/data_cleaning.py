"""Clean and enrich Indian agricultural mandi price CSV files."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from common import (
    CLEANED_DIR,
    RAW_DIR,
    TARGET_COMMODITIES,
    ensure_directories,
    standardize_columns,
)


OUTPUT_PATH = CLEANED_DIR / "mandi_cleaned_master.csv"
REPORT_PATH = CLEANED_DIR / "cleaning_report.json"
TEXT_COLUMNS = ("state", "district", "market", "commodity", "variety", "grade")
PRICE_COLUMNS = ("min_price", "max_price", "modal_price")
ROLLING_KEYS = ["commodity", "state", "district", "market"]

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)


def load_raw_files(raw_dir: Path = RAW_DIR) -> tuple[pd.DataFrame, list[str]]:
    """Load and standardize every CSV in the raw data directory."""
    csv_files = sorted(raw_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {raw_dir}")

    frames: list[pd.DataFrame] = []
    for csv_path in csv_files:
        LOGGER.info("Loading %s", csv_path.name)
        frame = pd.read_csv(csv_path, low_memory=False)
        frame = standardize_columns(frame)
        frame["source_file"] = csv_path.name
        frames.append(frame)

    return pd.concat(frames, ignore_index=True), [path.name for path in csv_files]


def season_from_month(month: pd.Series) -> pd.Series:
    """Classify months using India's broad crop-marketing seasons."""
    conditions = [
        month.isin([7, 8, 9, 10]),
        month.isin([11, 12, 1, 2, 3]),
        month.isin([4, 5, 6]),
    ]
    return pd.Series(
        np.select(conditions, ["Kharif", "Rabi", "Zaid"], default="Unknown"),
        index=month.index,
        dtype="string",
    )


def add_rolling_average(frame: pd.DataFrame) -> pd.DataFrame:
    """Attach a calendar-based 30-day mean for each commodity-market series."""
    daily = (
        frame.groupby(ROLLING_KEYS + ["arrival_date"], as_index=False, observed=True)[
            "modal_price"
        ]
        .mean()
        .sort_values(ROLLING_KEYS + ["arrival_date"])
    )
    rolling = (
        daily.groupby(ROLLING_KEYS, sort=False, observed=True)
        .rolling("30D", on="arrival_date", min_periods=1)["modal_price"]
        .mean()
        .rename("rolling_30d_avg")
        .reset_index()
    )
    return frame.merge(
        rolling,
        on=ROLLING_KEYS + ["arrival_date"],
        how="left",
        validate="many_to_one",
    )


def clean_data(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    """Apply documented quality rules and create analytical features."""
    report: dict[str, object] = {"input_rows": int(len(frame))}

    frame = frame.copy()
    for column in TEXT_COLUMNS:
        frame[column] = frame[column].astype("string").str.strip()

    normalized_targets = {name.casefold(): name for name in TARGET_COMMODITIES}
    frame["commodity"] = frame["commodity"].str.casefold().map(normalized_targets)
    target_mask = frame["commodity"].notna()
    report["rows_removed_non_target_commodity"] = int((~target_mask).sum())
    frame = frame.loc[target_mask].copy()

    for column in ("state", "district", "market"):
        frame[column] = frame[column].str.replace(r"\s+", " ", regex=True).str.title()
    frame["variety"] = (
        frame["variety"].fillna("Unknown").replace("", "Unknown").str.strip()
    )
    frame["grade"] = frame["grade"].fillna("Unknown").replace("", "Unknown").str.strip()

    frame["arrival_date"] = pd.to_datetime(
        frame["arrival_date"], errors="coerce", format="mixed", dayfirst=False
    )
    for column in PRICE_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    critical_columns = [
        "state",
        "district",
        "market",
        "commodity",
        "arrival_date",
        *PRICE_COLUMNS,
    ]
    missing_critical = frame[critical_columns].isna().any(axis=1)
    report["rows_removed_missing_or_invalid_critical_values"] = int(
        missing_critical.sum()
    )
    frame = frame.loc[~missing_critical].copy()

    non_positive = (frame[list(PRICE_COLUMNS)] <= 0).any(axis=1)
    report["rows_removed_non_positive_prices"] = int(non_positive.sum())
    frame = frame.loc[~non_positive].copy()

    invalid_range = frame["max_price"] < frame["min_price"]
    report["rows_removed_max_below_min"] = int(invalid_range.sum())
    frame = frame.loc[~invalid_range].copy()

    duplicate_mask = frame.duplicated(
        subset=[
            "state",
            "district",
            "market",
            "commodity",
            "variety",
            "grade",
            "arrival_date",
            *PRICE_COLUMNS,
        ],
        keep="first",
    )
    report["duplicate_rows_removed"] = int(duplicate_mask.sum())
    frame = frame.loc[~duplicate_mask].copy()

    frame["price_consistency_flag"] = np.where(
        frame["modal_price"].between(frame["min_price"], frame["max_price"]),
        0,
        1,
    )
    frame["year"] = frame["arrival_date"].dt.year.astype("int16")
    frame["month_number"] = frame["arrival_date"].dt.month.astype("int8")
    frame["month"] = frame["arrival_date"].dt.month_name()
    frame["year_month"] = frame["arrival_date"].dt.to_period("M").astype(str)
    frame["quarter"] = "Q" + frame["arrival_date"].dt.quarter.astype(str)
    frame["season"] = season_from_month(frame["month_number"])
    frame["price_range"] = frame["max_price"] - frame["min_price"]

    LOGGER.info("Calculating 30-day rolling averages")
    frame = add_rolling_average(frame)
    deviation = (
        (frame["modal_price"] - frame["rolling_30d_avg"]).abs()
        / frame["rolling_30d_avg"]
    )
    frame["price_deviation_pct"] = deviation * 100
    frame["price_volatility_flag"] = (deviation > 0.30).astype("int8")

    commodity_stats = frame.groupby("commodity", observed=True)["modal_price"].agg(
        commodity_mean="mean", commodity_std="std"
    )
    frame = frame.join(commodity_stats, on="commodity")
    frame["price_z_score"] = (
        frame["modal_price"] - frame["commodity_mean"]
    ) / frame["commodity_std"]
    frame["anomaly_flag"] = (frame["price_z_score"].abs() > 2).astype("int8")
    frame = frame.drop(columns=["commodity_mean", "commodity_std", "source_file"])

    frame = frame.sort_values(
        ["arrival_date", "commodity", "state", "district", "market"],
        kind="stable",
    ).reset_index(drop=True)

    report.update(
        {
            "output_rows": int(len(frame)),
            "date_min": frame["arrival_date"].min().date().isoformat(),
            "date_max": frame["arrival_date"].max().date().isoformat(),
            "commodities": sorted(frame["commodity"].unique().tolist()),
            "anomaly_rows": int(frame["anomaly_flag"].sum()),
            "volatility_flag_rows": int(frame["price_volatility_flag"].sum()),
            "modal_outside_min_max_rows_retained": int(
                frame["price_consistency_flag"].sum()
            ),
            "missing_value_policy": {
                "critical_dimensions_dates_prices": "Drop rows that remain missing or fail parsing.",
                "variety_and_grade": "Fill blank values with 'Unknown'.",
                "non_positive_prices": "Drop because mandi prices must be positive.",
                "max_below_min": "Drop because the quoted range is internally invalid.",
                "modal_outside_range": "Retain and flag for audit; these may be source errors or genuine unusual quotes.",
            },
        }
    )
    return frame, report


def main() -> None:
    """Run the complete cleaning workflow and export its audit report."""
    ensure_directories()
    raw, source_files = load_raw_files()
    cleaned, report = clean_data(raw)
    report["source_files"] = source_files

    cleaned.to_csv(OUTPUT_PATH, index=False, date_format="%Y-%m-%d")
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    LOGGER.info("Wrote %s rows to %s", f"{len(cleaned):,}", OUTPUT_PATH)
    LOGGER.info("Wrote cleaning decisions and row counts to %s", REPORT_PATH)


if __name__ == "__main__":
    main()
