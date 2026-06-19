"""Generate plain-English, data-backed mandi price insights."""

from __future__ import annotations

import logging

import pandas as pd

from common import INSIGHTS_DIR, currency, ensure_directories, read_cleaned_data


OUTPUT_PATH = INSIGHTS_DIR / "automated_insights.txt"
STD_THRESHOLD = 2.0
MIN_MONTHLY_OBSERVATIONS = 30
MIN_STATE_OBSERVATIONS = 30
MIN_MARKET_OBSERVATIONS = 30
REQUIRED_COLUMNS = {
    "arrival_date",
    "state",
    "market",
    "commodity",
    "season",
    "modal_price",
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)


def validate_input(frame: pd.DataFrame) -> None:
    """Verify that the cleaned dataset can support every requested insight."""
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"Cleaned data is missing columns: {', '.join(missing)}")
    if frame.empty:
        raise ValueError("Cleaned data contains no rows.")
    if not pd.api.types.is_datetime64_any_dtype(frame["arrival_date"]):
        raise TypeError("arrival_date must be loaded as a datetime column.")


def top_monthly_spike(frame: pd.DataFrame) -> str:
    """Find the strongest supported month-over-month commodity-state increase."""
    monthly = (
        frame.groupby(
            ["commodity", "state", pd.Grouper(key="arrival_date", freq="MS")],
            observed=True,
        )["modal_price"]
        .agg(avg_modal_price="mean", observations="size")
        .reset_index()
        .sort_values(["commodity", "state", "arrival_date"])
    )
    grouped = monthly.groupby(["commodity", "state"], observed=True)
    monthly["previous_price"] = grouped["avg_modal_price"].shift()
    monthly["previous_observations"] = grouped["observations"].shift()
    monthly["previous_month"] = grouped["arrival_date"].shift()
    monthly["change_pct"] = (
        (monthly["avg_modal_price"] - monthly["previous_price"])
        / monthly["previous_price"]
        * 100
    )
    month_gap = (
        monthly["arrival_date"].dt.to_period("M")
        - monthly["previous_month"].dt.to_period("M")
    ).apply(lambda value: value.n if pd.notna(value) else pd.NA)
    valid = monthly.loc[
        monthly["previous_price"].gt(0)
        & monthly["change_pct"].notna()
        & monthly["observations"].ge(MIN_MONTHLY_OBSERVATIONS)
        & monthly["previous_observations"].ge(MIN_MONTHLY_OBSERVATIONS)
        & month_gap.eq(1)
    ]
    if valid.empty:
        raise ValueError(
            "No consecutive commodity-state months meet the minimum "
            f"{MIN_MONTHLY_OBSERVATIONS}-observation threshold."
        )
    row = valid.loc[valid["change_pct"].idxmax()]
    insight = (
        f"Top price spike: {row['commodity']} in {row['state']} rose "
        f"{row['change_pct']:.1f}% in {row['arrival_date']:%B %Y} versus the prior month, "
        f"from {currency(row['previous_price'])} to "
        f"{currency(row['avg_modal_price'])}. Both monthly averages contain at "
        f"least {MIN_MONTHLY_OBSERVATIONS} quotes."
    )
    commodity_median = frame.loc[
        frame["commodity"].eq(row["commodity"]), "modal_price"
    ].median()
    if row["previous_price"] < commodity_median * 0.25:
        insight += (
            f" The prior-month baseline is below 25% of the commodity's overall "
            f"median ({currency(commodity_median)}), so the jump should be reviewed "
            "for a possible unit or source-data discontinuity."
        )
    return insight


def most_volatile_crop(frame: pd.DataFrame) -> str:
    """Rank commodities using coefficient of variation."""
    stats = frame.groupby("commodity", observed=True)["modal_price"].agg(["mean", "std"])
    stats["cv_pct"] = stats["std"] / stats["mean"] * 100
    commodity = stats["cv_pct"].idxmax()
    return (
        f"Most volatile crop: {commodity} has the highest coefficient of variation "
        f"at {stats.loc[commodity, 'cv_pct']:.1f}%. Its standard deviation is "
        f"{currency(stats.loc[commodity, 'std'])} against an average of "
        f"{currency(stats.loc[commodity, 'mean'])}, indicating the widest price "
        "dispersion relative to its average."
    )


def cheapest_states(frame: pd.DataFrame) -> str:
    """Return the lowest supported average-price state for every commodity."""
    grouped = (
        frame.groupby(["commodity", "state"], observed=True)["modal_price"]
        .agg(avg_modal_price="mean", observations="size")
        .reset_index()
    )
    eligible = grouped.loc[
        grouped["observations"].ge(MIN_STATE_OBSERVATIONS)
    ].copy()
    missing = sorted(set(frame["commodity"].unique()) - set(eligible["commodity"]))
    if missing:
        raise ValueError(
            "No state meets the observation threshold for: " + ", ".join(missing)
        )
    cheapest = eligible.loc[
        eligible.groupby("commodity")["avg_modal_price"].idxmin()
    ]
    details = "; ".join(
        f"{row.commodity}: {row.state} "
        f"({currency(row.avg_modal_price)}, {row.observations:,} quotes)"
        for row in cheapest.sort_values("commodity").itertuples()
    )
    return (
        f"Cheapest state by commodity among states with at least "
        f"{MIN_STATE_OBSERVATIONS} quotes: {details}."
    )


def most_expensive_market(frame: pd.DataFrame) -> str:
    """Identify the market with the highest average modal price."""
    grouped = (
        frame.groupby(["state", "market"], observed=True)["modal_price"]
        .agg(avg_modal_price="mean", observations="size")
    )
    grouped = grouped.loc[
        grouped["observations"].ge(MIN_MARKET_OBSERVATIONS)
    ]
    if grouped.empty:
        raise ValueError("No market meets the minimum observation threshold.")
    state, market = grouped["avg_modal_price"].idxmax()
    row = grouped.loc[(state, market)]
    return (
        f"Most expensive established market: {market}, {state}, averages "
        f"{currency(row['avg_modal_price'])} across {int(row['observations']):,} "
        f"quotes."
    )


def seasonal_pattern(frame: pd.DataFrame) -> str:
    """Summarize each commodity's observed high and low price seasons."""
    grouped = (
        frame.groupby(["commodity", "season"], observed=True)["modal_price"]
        .mean()
        .rename("avg_modal_price")
        .reset_index()
    )
    details: list[str] = []
    for commodity, commodity_prices in grouped.groupby(
        "commodity", observed=True, sort=True
    ):
        if len(commodity_prices) == 1:
            only = commodity_prices.iloc[0]
            details.append(
                f"{commodity} has observations only in {only['season']} "
                f"({currency(only['avg_modal_price'])}), so no cross-season "
                "comparison is available"
            )
            continue
        high = commodity_prices.loc[commodity_prices["avg_modal_price"].idxmax()]
        low = commodity_prices.loc[commodity_prices["avg_modal_price"].idxmin()]
        difference = (
            high["avg_modal_price"] / low["avg_modal_price"] - 1
        ) * 100
        details.append(
            f"{commodity} peaks in {high['season']} at "
            f"{currency(high['avg_modal_price'])}, {difference:.1f}% above its "
            f"{low['season']} average"
        )
    return "Seasonal pattern: " + "; ".join(details) + "."


def anomaly_summary(frame: pd.DataFrame) -> str:
    """Recalculate and summarize commodity-level two-standard-deviation flags."""
    stats = frame.groupby("commodity", observed=True)["modal_price"].agg(
        commodity_mean="mean",
        commodity_std="std",
    )
    scored = frame.join(stats, on="commodity")
    scored["z_score"] = (
        scored["modal_price"] - scored["commodity_mean"]
    ) / scored["commodity_std"]
    anomalies = scored.loc[scored["z_score"].abs() > STD_THRESHOLD]
    if anomalies.empty:
        return "Anomaly summary: no records breach the two-standard-deviation rule."
    commodity = anomalies["commodity"].value_counts().idxmax()
    state = anomalies["state"].value_counts().idxmax()
    high_count = int(anomalies["z_score"].gt(STD_THRESHOLD).sum())
    low_count = int(anomalies["z_score"].lt(-STD_THRESHOLD).sum())
    return (
        f"Anomaly summary: {len(anomalies):,} records ({len(anomalies) / len(frame) * 100:.2f}%) "
        f"breach the commodity-level two-standard-deviation rule: "
        f"{high_count:,} high spikes and {low_count:,} low drops. {commodity} "
        f"contributes the most flags, and {state} has the largest state-level count."
    )


def main() -> None:
    """Write all automated insights to a text artifact."""
    ensure_directories()
    frame = read_cleaned_data()
    validate_input(frame)
    insights = [
        "INDIAN AGRICULTURAL MANDI PRICE - AUTOMATED INSIGHTS",
        "=" * 54,
        f"Coverage: {frame['arrival_date'].min():%d %B %Y} to "
        f"{frame['arrival_date'].max():%d %B %Y} | "
        f"{len(frame):,} cleaned market quotes",
        "",
        "1. " + top_monthly_spike(frame),
        "2. " + most_volatile_crop(frame),
        "3. " + cheapest_states(frame),
        "4. " + most_expensive_market(frame),
        "5. " + seasonal_pattern(frame),
        "6. " + anomaly_summary(frame),
        "",
        "Interpretation note: statistical relationships indicate where to investigate. "
        "They do not establish weather, logistics, market power, or policy as causal factors.",
    ]
    OUTPUT_PATH.write_text("\n".join(insights) + "\n", encoding="utf-8")
    LOGGER.info("Wrote automated insights to %s", OUTPUT_PATH)


if __name__ == "__main__":
    main()
