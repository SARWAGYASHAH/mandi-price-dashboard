"""Forecast national Onion and Tomato modal prices with Prophet."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

from common import (
    INSIGHTS_DIR,
    OUTPUT_DIR,
    VISUALS_DIR,
    ensure_directories,
    read_cleaned_data,
)


FORECAST_DAYS = 90
FORECAST_COMMODITIES = ("Onion", "Tomato")
ACCURACY_PATH = INSIGHTS_DIR / "forecast_accuracy.md"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ForecastMetric:
    commodity: str
    mae: float
    rmse: float
    mape: float
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    test_days: int


def prepare_observed_series(frame: pd.DataFrame, commodity: str) -> pd.DataFrame:
    """Aggregate market quotes to one observed national daily median."""
    daily = (
        frame.loc[frame["commodity"].eq(commodity)]
        .groupby("arrival_date", as_index=True)["modal_price"]
        .median()
        .sort_index()
    )
    if daily.empty:
        raise ValueError(f"No cleaned observations are available for {commodity}.")
    return daily.rename("y").rename_axis("ds").reset_index()


def fill_calendar_gaps(series: pd.DataFrame) -> pd.DataFrame:
    """Create a continuous modeling series without crossing a holdout boundary."""
    daily = series.set_index("ds")["y"].sort_index()
    full_index = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    daily = daily.reindex(full_index).interpolate(method="time").ffill().bfill()
    return daily.rename("y").rename_axis("ds").reset_index()


def build_model(series: pd.DataFrame) -> Prophet:
    """Configure seasonality only when the available history supports it."""
    history_days = (series["ds"].max() - series["ds"].min()).days
    return Prophet(
        interval_width=0.80,
        yearly_seasonality=history_days >= 365,
        weekly_seasonality=True,
        daily_seasonality=False,
        seasonality_mode="multiplicative",
        changepoint_prior_scale=0.08,
    )


def evaluate(series: pd.DataFrame, commodity: str) -> ForecastMetric:
    """Evaluate on a chronological holdout sized to the available history."""
    test_days = min(FORECAST_DAYS, max(30, round(len(series) * 0.20)))
    train_observed = series.iloc[:-test_days].copy()
    test = series.iloc[-test_days:].copy()
    if train_observed["ds"].nunique() < 90:
        raise ValueError(f"{commodity} does not have enough history for evaluation.")

    train = fill_calendar_gaps(train_observed)
    model = build_model(train)
    np.random.seed(42)
    model.fit(train)
    predicted = model.predict(test[["ds"]])

    actual = test["y"].to_numpy()
    forecast = predicted["yhat"].clip(lower=0).to_numpy()
    mae = mean_absolute_error(actual, forecast)
    rmse = root_mean_squared_error(actual, forecast)
    non_zero = actual != 0
    mape = np.mean(np.abs((actual[non_zero] - forecast[non_zero]) / actual[non_zero])) * 100
    return ForecastMetric(
        commodity=commodity,
        mae=float(mae),
        rmse=float(rmse),
        mape=float(mape),
        train_start=train["ds"].min().date().isoformat(),
        train_end=train["ds"].max().date().isoformat(),
        test_start=test["ds"].min().date().isoformat(),
        test_end=test["ds"].max().date().isoformat(),
        test_days=len(test),
    )


def forecast_future(series: pd.DataFrame, commodity: str) -> pd.DataFrame:
    """Refit on all observations and forecast the next 90 calendar days."""
    series = fill_calendar_gaps(series)
    model = build_model(series)
    np.random.seed(42)
    model.fit(series)
    future = model.make_future_dataframe(periods=FORECAST_DAYS, freq="D")
    predicted = model.predict(future)
    future_only = predicted.loc[predicted["ds"] > series["ds"].max()].copy()
    result = future_only.loc[:, ["ds", "yhat", "yhat_lower", "yhat_upper"]].rename(
        columns={
            "ds": "forecast_date",
            "yhat": "forecast_modal_price",
            "yhat_lower": "forecast_lower_80",
            "yhat_upper": "forecast_upper_80",
        }
    )
    numeric_columns = [
        "forecast_modal_price",
        "forecast_lower_80",
        "forecast_upper_80",
    ]
    result[numeric_columns] = result[numeric_columns].clip(lower=0).round(2)
    result.insert(0, "commodity", commodity)
    return result


def save_plot(
    series: pd.DataFrame, forecast: pd.DataFrame, commodity: str
) -> None:
    """Save a clean historical-and-forecast chart for reports and the website."""
    history = series.loc[
        series["ds"] >= series["ds"].max() - pd.Timedelta(days=364)
    ]
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(history["ds"], history["y"], color="#94a3b8", linewidth=1.4, label="Daily median")
    ax.plot(
        forecast["forecast_date"],
        forecast["forecast_modal_price"],
        color="#f59e0b",
        linewidth=2.4,
        label="90-day forecast",
    )
    ax.fill_between(
        forecast["forecast_date"],
        forecast["forecast_lower_80"],
        forecast["forecast_upper_80"],
        color="#f59e0b",
        alpha=0.18,
        label="80% interval",
    )
    ax.axvline(series["ds"].max(), color="#475569", linestyle="--", linewidth=1)
    ax.set_title(f"{commodity} Modal Price: 90-Day Forecast", loc="left", weight="bold")
    ax.set_ylabel("INR per quintal")
    ax.set_xlabel("")
    ax.grid(axis="y", alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, ncol=3)
    fig.tight_layout()
    fig.savefig(VISUALS_DIR / f"{commodity.lower()}_forecast.png", dpi=180)
    plt.close(fig)


def write_accuracy_report(metrics: list[ForecastMetric]) -> None:
    """Document the holdout method and measured model errors."""
    lines = [
        "# Forecast Accuracy",
        "",
        "Prophet is evaluated with a chronological holdout containing up to 90 observed "
        "daily values, capped at 20% of each commodity's history with a 30-day minimum. "
        "This adaptive rule preserves enough training data for Tomato's shorter series. "
        "The target is the national daily median modal price, chosen to reduce the influence "
        "of isolated data-entry errors while preserving the market-level price signal.",
        "",
        "| Commodity | MAE (INR/qtl) | RMSE (INR/qtl) | MAPE | Holdout observations | Holdout period |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for metric in metrics:
        lines.append(
            f"| {metric.commodity} | {metric.mae:,.2f} | {metric.rmse:,.2f} | "
            f"{metric.mape:.2f}% | {metric.test_days} | "
            f"{metric.test_start} to {metric.test_end} |"
        )
    lines.extend(
        [
            "",
            "## Method",
            "",
            f"- Forecast horizon: {FORECAST_DAYS} days.",
            "- Features: Prophet trend, weekly seasonality, and multiplicative seasonal effects. Yearly seasonality is enabled only when at least 365 days of history are available.",
            "- Validation: chronological holdout; no future observations are used to fit the evaluation model.",
            "- Final forecasts: each model is refit on all available observations before generating future values.",
            "- Intervals: exported lower and upper bounds are Prophet's 80% uncertainty interval.",
            "- Coverage caveat: Tomato data ends on 2023-11-06, so its 90-day projection is a historical back-cast artifact relative to the full dataset and carries substantially more uncertainty than Onion.",
            "",
            "These forecasts are analytical baselines, not trading advice. Weather, arrivals, policy changes, "
            "storage conditions, and market closures should be added before operational deployment.",
        ]
    )
    ACCURACY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Evaluate and export Onion and Tomato forecasts."""
    ensure_directories()
    frame = read_cleaned_data()
    metrics: list[ForecastMetric] = []
    for commodity in FORECAST_COMMODITIES:
        LOGGER.info("Evaluating %s forecast", commodity)
        series = prepare_observed_series(frame, commodity)
        metrics.append(evaluate(series, commodity))

        LOGGER.info("Fitting final %s model", commodity)
        forecast = forecast_future(series, commodity)
        forecast.to_csv(
            OUTPUT_DIR / f"{commodity.lower()}_forecast.csv",
            index=False,
            date_format="%Y-%m-%d",
        )
        save_plot(series, forecast, commodity)
    write_accuracy_report(metrics)
    LOGGER.info("Wrote forecasts, charts, and %s", ACCURACY_PATH)


if __name__ == "__main__":
    main()
