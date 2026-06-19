"""Create record-level and summary reports for commodity price anomalies."""

from __future__ import annotations

import logging
from collections.abc import Iterable

import numpy as np
import pandas as pd

from common import INSIGHTS_DIR, OUTPUT_DIR, currency, ensure_directories, read_cleaned_data


OUTPUT_PATH = OUTPUT_DIR / "anomaly_report.csv"
SUMMARY_PATH = INSIGHTS_DIR / "anomaly_summary.md"
STD_THRESHOLD = 2.0
REQUIRED_COLUMNS = {
    "arrival_date",
    "state",
    "district",
    "market",
    "commodity",
    "variety",
    "grade",
    "min_price",
    "max_price",
    "modal_price",
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)


def validate_input(frame: pd.DataFrame) -> None:
    """Fail early when the cleaned dataset cannot support the analysis."""
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"Cleaned data is missing columns: {', '.join(missing)}")
    if frame.empty:
        raise ValueError("Cleaned data contains no rows.")
    if not pd.api.types.is_datetime64_any_dtype(frame["arrival_date"]):
        raise TypeError("arrival_date must be loaded as a datetime column.")
    if frame["modal_price"].isna().any():
        raise ValueError("modal_price contains missing values.")


def build_anomaly_report(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply the two-standard-deviation rule within each commodity."""
    validate_input(frame)
    stats = frame.groupby("commodity", observed=True)["modal_price"].agg(
        commodity_mean="mean",
        commodity_std="std",
        commodity_observations="size",
    )
    invalid_std = stats["commodity_std"].isna() | stats["commodity_std"].eq(0)
    if invalid_std.any():
        commodities = ", ".join(stats.index[invalid_std].astype(str))
        raise ValueError(
            "Cannot calculate z-scores for commodities with zero or undefined "
            f"standard deviation: {commodities}"
        )

    enriched = frame.join(stats, on="commodity")
    enriched["price_z_score"] = (
        enriched["modal_price"] - enriched["commodity_mean"]
    ) / enriched["commodity_std"]
    anomalies = enriched.loc[
        enriched["price_z_score"].abs() > STD_THRESHOLD
    ].copy()

    anomalies["anomaly_type"] = np.where(
        anomalies["price_z_score"] > STD_THRESHOLD,
        "High Price Spike",
        "Low Price Drop",
    )
    anomalies["deviation_from_commodity_mean_pct"] = (
        (anomalies["modal_price"] - anomalies["commodity_mean"])
        / anomalies["commodity_mean"]
        * 100
    )
    anomalies["anomaly_explanation"] = np.where(
        anomalies["price_z_score"] > STD_THRESHOLD,
        "The modal price is more than two commodity-level standard deviations "
        "above the mean. It is an unusually expensive quote that should be "
        "checked for scarcity, quality premiums, disruption, or data error.",
        "The modal price is more than two commodity-level standard deviations "
        "below the mean. It is an unusually cheap quote that should be checked "
        "for oversupply, distress sales, low grade, or data error.",
    )
    anomalies["month"] = anomalies["arrival_date"].dt.month_name()
    columns = [
        "arrival_date",
        "month",
        "state",
        "district",
        "market",
        "commodity",
        "variety",
        "grade",
        "min_price",
        "max_price",
        "modal_price",
        "commodity_mean",
        "commodity_std",
        "commodity_observations",
        "price_z_score",
        "deviation_from_commodity_mean_pct",
        "anomaly_type",
        "anomaly_explanation",
    ]
    return anomalies.loc[:, columns].sort_values(
        ["price_z_score", "arrival_date"],
        key=lambda series: series.abs()
        if series.name == "price_z_score"
        else series,
        ascending=[False, False],
        kind="stable",
    )


def markdown_table(
    rows: Iterable[tuple[str, int, float]],
    first_column: str,
) -> list[str]:
    """Format count-and-rate rows as a compact Markdown table."""
    lines = [
        f"| {first_column} | Anomalies | Anomaly rate |",
        "|---|---:|---:|",
    ]
    lines.extend(
        f"| {label} | {count:,} | {rate:.2f}% |"
        for label, count, rate in rows
    )
    return lines


def concentration_rows(
    frame: pd.DataFrame,
    anomalies: pd.DataFrame,
    column: str,
    limit: int = 5,
) -> list[tuple[str, int, float]]:
    """Return groups with the largest anomaly counts and their within-group rates."""
    total_counts = frame[column].value_counts()
    anomaly_counts = anomalies[column].value_counts()
    return [
        (
            str(label),
            int(count),
            float(count / total_counts.loc[label] * 100),
        )
        for label, count in anomaly_counts.head(limit).items()
    ]


def write_summary(frame: pd.DataFrame, anomalies: pd.DataFrame) -> None:
    """Write an interview-friendly anomaly summary backed by observed data."""
    total_rows = len(frame)
    anomaly_rate = len(anomalies) / total_rows * 100
    lines = [
        "# Anomaly Detection Summary",
        "",
        "## Method",
        "",
        f"Each quote is compared with its commodity mean. A record is flagged when "
        f"its modal price is more than {STD_THRESHOLD:.0f} standard deviations "
        "above or below that mean. Commodity-level thresholds keep crops with "
        "different normal price ranges comparable.",
        "",
        "A statistical flag is a review signal, not proof of manipulation. Confirm "
        "flags against arrivals, grade, weather, holidays, and neighboring markets.",
        "",
        "## Overall Results",
        "",
        f"- Records analysed: **{total_rows:,}**.",
        f"- Records flagged: **{len(anomalies):,}** ({anomaly_rate:.2f}%).",
    ]

    if anomalies.empty:
        lines.extend(
            [
                "- No records exceeded the configured threshold.",
                "",
                "## Anomaly Types",
                "",
                "- **High Price Spike:** no observations detected.",
                "- **Low Price Drop:** no observations detected.",
            ]
        )
        SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    commodity_counts = anomalies["commodity"].value_counts()
    state_counts = anomalies["state"].value_counts()
    type_counts = anomalies["anomaly_type"].value_counts()
    month_totals = frame["arrival_date"].dt.month_name().value_counts()
    month_counts = anomalies["month"].value_counts()
    month_rows = [
        (
            str(month),
            int(count),
            float(count / month_totals.loc[month] * 100),
        )
        for month, count in month_counts.head(5).items()
    ]

    lines.extend(
        [
            f"- Commodity with the most anomalies: **{commodity_counts.index[0]}** "
            f"({commodity_counts.iloc[0]:,}).",
            f"- State with the most anomalies: **{state_counts.index[0]}** "
            f"({state_counts.iloc[0]:,}).",
            f"- Month with the most anomalies: **{month_counts.index[0]}** "
            f"({month_counts.iloc[0]:,}).",
            f"- High price spikes: **{type_counts.get('High Price Spike', 0):,}**.",
            f"- Low price drops: **{type_counts.get('Low Price Drop', 0):,}**.",
            "",
            "## Commodity Concentration",
            "",
            *markdown_table(
                concentration_rows(frame, anomalies, "commodity"),
                "Commodity",
            ),
            "",
            "## State Concentration",
            "",
            *markdown_table(
                concentration_rows(frame, anomalies, "state"),
                "State",
            ),
            "",
            "## Most Anomaly-Prone Months",
            "",
            *markdown_table(month_rows, "Month"),
            "",
            "Months are ordered by flagged-record count. The rate controls for the "
            "number of source records available in each month.",
            "",
            "## Anomaly Types",
            "",
            "- **High Price Spike:** the quote is over two commodity-level standard "
            "deviations above the mean. Possible explanations include local scarcity, "
            "quality premiums, weather disruption, or reporting errors.",
            "- **Low Price Drop:** the quote is over two commodity-level standard "
            "deviations below the mean. Possible explanations include supply gluts, "
            "distress sales, low-grade produce, or reporting errors.",
            "",
            "## Extreme Observations",
            "",
        ]
    )

    high = anomalies.loc[anomalies["anomaly_type"].eq("High Price Spike")]
    low = anomalies.loc[anomalies["anomaly_type"].eq("Low Price Drop")]
    if not high.empty:
        extreme_high = high.loc[high["price_z_score"].idxmax()]
        lines.append(
            f"- Highest spike: **{extreme_high['commodity']}** at "
            f"**{extreme_high['market']}, {extreme_high['state']}** on "
            f"**{extreme_high['arrival_date'].date().isoformat()}** recorded "
            f"{currency(extreme_high['modal_price'])}, a z-score of "
            f"**{extreme_high['price_z_score']:.2f}**."
        )
    if not low.empty:
        extreme_low = low.loc[low["price_z_score"].idxmin()]
        lines.append(
            f"- Lowest drop: **{extreme_low['commodity']}** at "
            f"**{extreme_low['market']}, {extreme_low['state']}** on "
            f"**{extreme_low['arrival_date'].date().isoformat()}** recorded "
            f"{currency(extreme_low['modal_price'])}, a z-score of "
            f"**{extreme_low['price_z_score']:.2f}**."
        )
    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Generate anomaly records and a concise markdown summary."""
    ensure_directories()
    frame = read_cleaned_data()
    anomalies = build_anomaly_report(frame)
    anomalies.to_csv(OUTPUT_PATH, index=False, date_format="%Y-%m-%d")
    write_summary(frame, anomalies)
    LOGGER.info("Wrote %s anomaly records to %s", f"{len(anomalies):,}", OUTPUT_PATH)
    LOGGER.info("Wrote anomaly summary to %s", SUMMARY_PATH)


if __name__ == "__main__":
    main()
