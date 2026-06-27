"""Generate four data-backed dashboard previews for the Power BI build guide."""

from __future__ import annotations

import json
import logging
from urllib.request import urlopen

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize
from matplotlib.patches import Polygon

from common import POWERBI_DIR, ensure_directories, read_cleaned_data


OUTPUT_DIR = POWERBI_DIR / "dashboard_screenshots"
INDIA_STATES_URL = (
    "https://raw.githubusercontent.com/datameet/maps/master/"
    "website/docs/data/geojson/states.geojson"
)

BG = "#071923"
PANEL = "#0E2835"
GRID = "#274452"
TEXT = "#F4F7F5"
MUTED = "#9FB2BC"
SAFFRON = "#F4A261"
GREEN = "#2A9D8F"
RED = "#E76F51"
BLUE = "#62B6CB"
PALETTE = [SAFFRON, GREEN, BLUE, "#C77DFF", "#E9C46A"]

STATE_MAP_ALIASES = {
    "Andaman & Nicobar Island": "Andaman and Nicobar Islands",
    "Arunanchal Pradesh": "Arunachal Pradesh",
    "Jammu & Kashmir": "Jammu and Kashmir",
    "NCT of Delhi": "Delhi",
    "Orissa": "Odisha",
    "Uttaranchal": "Uttarakhand",
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)


def style_axis(ax: plt.Axes, title: str) -> None:
    """Apply the shared dark dashboard panel style."""
    ax.set_facecolor(PANEL)
    ax.set_title(title, loc="left", color=TEXT, fontsize=11, weight="bold", pad=10)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(axis="y", color=GRID, alpha=0.55, linewidth=0.7)
    for spine in ax.spines.values():
        spine.set_visible(False)


def make_figure(title: str, subtitle: str) -> plt.Figure:
    """Create a 16:9 report canvas with a consistent heading."""
    fig = plt.figure(figsize=(12.8, 7.2), facecolor=BG)
    fig.text(0.045, 0.955, title, color=TEXT, fontsize=20, weight="bold", va="top")
    fig.text(0.045, 0.918, subtitle, color=MUTED, fontsize=9, va="top")
    fig.text(
        0.955,
        0.95,
        "Date | Commodity | State | Season",
        color=MUTED,
        fontsize=8,
        ha="right",
        va="top",
        bbox={"boxstyle": "round,pad=0.5", "facecolor": PANEL, "edgecolor": GRID},
    )
    return fig


def add_cards(
    fig: plt.Figure,
    cards: list[tuple[str, str, str]],
    top: float = 0.82,
) -> None:
    """Add evenly spaced KPI cards."""
    left = 0.045
    gap = 0.012
    width = (0.91 - gap * (len(cards) - 1)) / len(cards)
    for index, (label, value, accent) in enumerate(cards):
        ax = fig.add_axes([left + index * (width + gap), top, width, 0.08])
        ax.set_facecolor(PANEL)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color(GRID)
        ax.text(0.04, 0.68, label.upper(), color=MUTED, fontsize=7, weight="bold")
        ax.text(0.04, 0.18, value, color=TEXT, fontsize=15, weight="bold")
        ax.axvline(0, color=accent, linewidth=5)


def save(fig: plt.Figure, page: int) -> None:
    """Write a dashboard preview and close the Matplotlib figure."""
    path = OUTPUT_DIR / f"page{page}.png"
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    LOGGER.info("Wrote %s", path)


def page_one(frame: pd.DataFrame) -> None:
    """National executive overview."""
    fig = make_figure(
        "National Overview",
        "Indian Agricultural Mandi Price Analysis | 06 Jun 2023 - 11 Jun 2025",
    )
    add_cards(
        fig,
        [
            ("Average modal price", f"INR {frame.modal_price.mean():,.0f}", SAFFRON),
            ("Market entries", f"{len(frame):,}", GREEN),
            ("Markets covered", f"{frame.market.nunique():,}", BLUE),
            ("Anomaly flags", f"{int(frame.anomaly_flag.sum()):,}", RED),
            (
                "Volatility flags",
                f"{int(frame.price_volatility_flag.sum()):,}",
                "#E9C46A",
            ),
        ],
    )

    ax_trend = fig.add_axes([0.045, 0.40, 0.59, 0.36])
    style_axis(ax_trend, "Monthly average modal price by commodity")
    monthly = (
        frame.groupby(
            ["commodity", pd.Grouper(key="arrival_date", freq="MS")],
            observed=True,
        )["modal_price"]
        .mean()
        .reset_index()
    )
    for color, (commodity, values) in zip(
        PALETTE, monthly.groupby("commodity", observed=True, sort=True)
    ):
        ax_trend.plot(
            values["arrival_date"],
            values["modal_price"],
            label=commodity,
            color=color,
            linewidth=2,
        )
    ax_trend.set_ylabel("INR / quintal", color=MUTED, fontsize=8)
    ax_trend.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax_trend.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax_trend.legend(
        frameon=False, labelcolor=TEXT, fontsize=7, ncol=5, loc="upper left"
    )

    ax_crop = fig.add_axes([0.665, 0.40, 0.29, 0.36])
    style_axis(ax_crop, "Average price by crop")
    crop_avg = frame.groupby("commodity", observed=True)["modal_price"].mean().sort_values()
    ax_crop.barh(crop_avg.index, crop_avg.values, color=PALETTE)
    for y, value in enumerate(crop_avg.values):
        ax_crop.text(value, y, f"  {value:,.0f}", va="center", color=TEXT, fontsize=8)
    ax_crop.set_xlabel("INR / quintal", color=MUTED, fontsize=8)

    ax_season = fig.add_axes([0.045, 0.075, 0.59, 0.25])
    style_axis(ax_season, "Seasonal price comparison")
    seasonal = (
        frame.pivot_table(
            index="commodity",
            columns="season",
            values="modal_price",
            aggfunc="mean",
        )
        .reindex(columns=["Kharif", "Rabi", "Zaid"])
        .sort_index()
    )
    x = np.arange(len(seasonal.index))
    width = 0.24
    for index, season in enumerate(seasonal.columns):
        ax_season.bar(
            x + (index - 1) * width,
            seasonal[season],
            width,
            label=season,
            color=[SAFFRON, GREEN, BLUE][index],
        )
    ax_season.set_xticks(x, seasonal.index)
    ax_season.legend(frameon=False, labelcolor=TEXT, fontsize=7, ncol=3)

    ax_anomaly = fig.add_axes([0.665, 0.075, 0.29, 0.25])
    style_axis(ax_anomaly, "Anomaly concentration")
    anomalies = (
        frame.loc[frame["anomaly_flag"].eq(1), "commodity"]
        .value_counts()
        .sort_values()
    )
    ax_anomaly.barh(anomalies.index, anomalies.values, color=RED, alpha=0.9)
    for y, value in enumerate(anomalies.values):
        ax_anomaly.text(value, y, f"  {value:,}", va="center", color=TEXT, fontsize=8)
    save(fig, 1)


def polygon_rings(geometry: dict[str, object]) -> list[list[list[float]]]:
    """Return exterior polygon rings from Polygon or MultiPolygon geometry."""
    coordinates = geometry["coordinates"]
    if geometry["type"] == "Polygon":
        return [coordinates[0]]
    if geometry["type"] == "MultiPolygon":
        return [polygon[0] for polygon in coordinates]
    return []


def page_two(frame: pd.DataFrame) -> None:
    """State comparison with an India filled map."""
    fig = make_figure(
        "State Wise Comparison",
        "Darker map shading indicates a higher average modal price",
    )
    state_stats = frame.groupby("state", observed=True).agg(
        avg_price=("modal_price", "mean"),
        entries=("modal_price", "size"),
        anomalies=("anomaly_flag", "sum"),
    )
    top_state = state_stats["avg_price"].idxmax()
    add_cards(
        fig,
        [
            ("States / UTs", f"{len(state_stats)}", GREEN),
            ("Highest average state", top_state, SAFFRON),
            (
                "Highest state average",
                f"INR {state_stats.loc[top_state, 'avg_price']:,.0f}",
                SAFFRON,
            ),
            (
                "Largest anomaly count",
                state_stats["anomalies"].idxmax(),
                RED,
            ),
        ],
    )

    ax_map = fig.add_axes([0.045, 0.075, 0.45, 0.685])
    ax_map.set_facecolor(PANEL)
    ax_map.set_title(
        "India filled map | Average modal price",
        loc="left",
        color=TEXT,
        fontsize=11,
        weight="bold",
        pad=10,
    )
    with urlopen(INDIA_STATES_URL, timeout=60) as response:
        geojson = json.load(response)
    norm = Normalize(
        vmin=float(state_stats["avg_price"].quantile(0.05)),
        vmax=float(state_stats["avg_price"].quantile(0.95)),
        clip=True,
    )
    cmap = plt.colormaps["YlOrBr"]
    for feature in geojson["features"]:
        source_name = feature["properties"]["ST_NM"]
        state_name = STATE_MAP_ALIASES.get(source_name, source_name)
        value = (
            float(state_stats.loc[state_name, "avg_price"])
            if state_name in state_stats.index
            else np.nan
        )
        color = cmap(norm(value)) if np.isfinite(value) else "#1A3A48"
        for ring in polygon_rings(feature["geometry"]):
            points = np.asarray(ring)
            ax_map.add_patch(
                Polygon(
                    points,
                    closed=True,
                    facecolor=color,
                    edgecolor="#75909B",
                    linewidth=0.35,
                )
            )
    ax_map.set_xlim(67, 98)
    ax_map.set_ylim(6, 38)
    ax_map.set_aspect("equal")
    ax_map.axis("off")
    colorbar = fig.colorbar(
        plt.cm.ScalarMappable(norm=norm, cmap=cmap),
        ax=ax_map,
        orientation="horizontal",
        fraction=0.035,
        pad=0.015,
    )
    colorbar.ax.tick_params(colors=MUTED, labelsize=7)
    colorbar.outline.set_visible(False)

    ax_rank = fig.add_axes([0.535, 0.40, 0.42, 0.36])
    style_axis(ax_rank, "Top 10 states by average modal price")
    ranked = state_stats.nlargest(10, "avg_price").sort_values("avg_price")
    ax_rank.barh(ranked.index, ranked["avg_price"], color=SAFFRON)
    for y, value in enumerate(ranked["avg_price"]):
        ax_rank.text(value, y, f"  {value:,.0f}", va="center", color=TEXT, fontsize=7)

    ax_scatter = fig.add_axes([0.535, 0.075, 0.42, 0.25])
    style_axis(ax_scatter, "Price level vs reporting coverage")
    sizes = 25 + 220 * (
        state_stats["anomalies"] / max(state_stats["anomalies"].max(), 1)
    )
    ax_scatter.scatter(
        state_stats["entries"],
        state_stats["avg_price"],
        s=sizes,
        c=state_stats["anomalies"],
        cmap="OrRd",
        alpha=0.8,
        edgecolors="none",
    )
    ax_scatter.set_xscale("log")
    ax_scatter.set_xlabel("Market entries (log scale)", color=MUTED, fontsize=8)
    ax_scatter.set_ylabel("Average modal price", color=MUTED, fontsize=8)
    for state in state_stats.nlargest(4, "avg_price").index:
        row = state_stats.loc[state]
        ax_scatter.annotate(
            state,
            (row["entries"], row["avg_price"]),
            color=TEXT,
            fontsize=7,
            xytext=(4, 3),
            textcoords="offset points",
        )
    save(fig, 2)


def page_three(frame: pd.DataFrame) -> None:
    """Crop deep dive using Onion as the selected crop."""
    crop = "Onion"
    selected = frame.loc[frame["commodity"].eq(crop)].copy()
    fig = make_figure(
        f"Crop Deep Dive | {crop}",
        "Commodity selector: Onion | State: All | Variety: All | Grade: All",
    )
    stats = selected["modal_price"].agg(["mean", "median", "std"])
    cv = stats["std"] / stats["mean"]
    add_cards(
        fig,
        [
            ("Average price", f"INR {stats['mean']:,.0f}", SAFFRON),
            ("Median price", f"INR {stats['median']:,.0f}", GREEN),
            ("Volatility index", f"{cv:.1%}", RED),
            ("Anomaly count", f"{int(selected.anomaly_flag.sum()):,}", RED),
            ("Observed states", f"{selected.state.nunique()}", BLUE),
        ],
    )

    ax_trend = fig.add_axes([0.045, 0.40, 0.62, 0.36])
    style_axis(ax_trend, "Daily median and 30-day rolling average")
    daily = selected.groupby("arrival_date")["modal_price"].median().sort_index()
    rolling = daily.rolling("30D", min_periods=1).mean()
    ax_trend.plot(daily.index, daily.values, color=MUTED, linewidth=1, label="Daily median")
    ax_trend.plot(rolling.index, rolling.values, color=SAFFRON, linewidth=2.4, label="30-day average")
    ax_trend.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax_trend.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax_trend.legend(frameon=False, labelcolor=TEXT, fontsize=8)

    ax_season = fig.add_axes([0.70, 0.40, 0.255, 0.36])
    style_axis(ax_season, "Seasonal average")
    seasonal = selected.groupby("season", observed=True)["modal_price"].mean().reindex(
        ["Kharif", "Rabi", "Zaid"]
    )
    bars = ax_season.bar(seasonal.index, seasonal.values, color=[SAFFRON, GREEN, BLUE])
    ax_season.bar_label(
        bars,
        labels=[f"{value:,.0f}" for value in seasonal.values],
        color=TEXT,
        fontsize=8,
        padding=3,
    )

    ax_state = fig.add_axes([0.13, 0.075, 0.34, 0.25])
    style_axis(ax_state, "Lowest supported state averages")
    state_price = selected.groupby("state", observed=True)["modal_price"].agg(["mean", "size"])
    state_price = state_price.loc[state_price["size"].ge(30)].nsmallest(8, "mean")
    ax_state.barh(
        state_price.index[::-1],
        state_price["mean"][::-1],
        color=GREEN,
    )

    ax_market = fig.add_axes([0.60, 0.075, 0.355, 0.25])
    style_axis(ax_market, "Most frequently reported Onion markets")
    markets = selected["market"].value_counts().head(8).sort_values()
    market_labels = [
        label if len(label) <= 25 else label[:22] + "..."
        for label in markets.index
    ]
    ax_market.barh(market_labels, markets.values, color=BLUE)
    for y, value in enumerate(markets.values):
        ax_market.text(value, y, f"  {value:,}", va="center", color=TEXT, fontsize=7)
    save(fig, 3)


def page_four(frame: pd.DataFrame) -> None:
    """Market intelligence and anomaly investigation page."""
    anomalies = frame.loc[frame["anomaly_flag"].eq(1)].copy()
    fig = make_figure(
        "Market Intelligence + Anomaly Flags",
        "Two-standard-deviation review signals | Statistical flags are not proof of manipulation",
    )
    add_cards(
        fig,
        [
            ("Anomaly records", f"{len(anomalies):,}", RED),
            ("Anomaly rate", f"{len(anomalies) / len(frame):.2%}", RED),
            ("High price spikes", f"{int(anomalies.price_z_score.gt(2).sum()):,}", SAFFRON),
            ("Low price drops", f"{int(anomalies.price_z_score.lt(-2).sum()):,}", BLUE),
            (
                "Range inconsistencies",
                f"{int(frame.price_consistency_flag.sum()):,}",
                "#E9C46A",
            ),
        ],
    )

    ax_state = fig.add_axes([0.105, 0.42, 0.23, 0.34])
    style_axis(ax_state, "States with most anomaly flags")
    state_counts = anomalies["state"].value_counts().head(8).sort_values()
    ax_state.barh(state_counts.index, state_counts.values, color=RED)

    ax_crop = fig.add_axes([0.40, 0.42, 0.19, 0.34])
    style_axis(ax_crop, "Anomalies by commodity")
    crop_counts = anomalies["commodity"].value_counts().sort_values()
    ax_crop.barh(crop_counts.index, crop_counts.values, color=SAFFRON)
    for y, value in enumerate(crop_counts.values):
        ax_crop.text(
            value * 0.97,
            y,
            f"{value:,}",
            va="center",
            ha="right",
            color=TEXT,
            fontsize=8,
        )

    ax_scatter = fig.add_axes([0.64, 0.42, 0.315, 0.34])
    style_axis(ax_scatter, "Observed vs rolling price")
    normal_sample = frame.loc[frame["anomaly_flag"].eq(0)].sample(
        n=min(2500, int(frame["anomaly_flag"].eq(0).sum())),
        random_state=42,
    )
    anomaly_sample = anomalies.sample(n=min(2500, len(anomalies)), random_state=42)
    ax_scatter.scatter(
        normal_sample["rolling_30d_avg"],
        normal_sample["modal_price"],
        s=5,
        color=MUTED,
        alpha=0.2,
        label="Normal",
    )
    ax_scatter.scatter(
        anomaly_sample["rolling_30d_avg"].clip(upper=20000),
        anomaly_sample["modal_price"].clip(upper=20000),
        s=8,
        color=RED,
        alpha=0.55,
        label="Anomaly",
    )
    ax_scatter.set_xlim(0, 20000)
    ax_scatter.set_ylim(0, 20000)
    ax_scatter.set_xlabel("30-day rolling average", color=MUTED, fontsize=8)
    ax_scatter.set_ylabel("Modal price", color=MUTED, fontsize=8)
    ax_scatter.legend(frameon=False, labelcolor=TEXT, fontsize=7)

    ax_table = fig.add_axes([0.045, 0.065, 0.91, 0.27])
    ax_table.set_facecolor(PANEL)
    ax_table.set_title(
        "Highest-severity records for investigation",
        loc="left",
        color=TEXT,
        fontsize=11,
        weight="bold",
        pad=10,
    )
    ax_table.axis("off")
    extreme = anomalies.nlargest(6, "price_z_score").copy()
    extreme["arrival_date"] = extreme["arrival_date"].dt.strftime("%d %b %Y")
    extreme["modal_price"] = extreme["modal_price"].map(lambda value: f"INR {value:,.0f}")
    extreme["price_z_score"] = extreme["price_z_score"].map(lambda value: f"{value:.2f}")
    table = ax_table.table(
        cellText=extreme[
            ["arrival_date", "commodity", "state", "market", "modal_price", "price_z_score"]
        ].values,
        colLabels=["Date", "Crop", "State", "Market", "Modal price", "Z-score"],
        cellLoc="left",
        colLoc="left",
        bbox=[0, 0, 1, 0.86],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7.5)
    for (row, _), cell in table.get_celld().items():
        cell.set_edgecolor(GRID)
        cell.set_facecolor("#163746" if row == 0 else PANEL)
        cell.get_text().set_color(TEXT if row == 0 else MUTED)
        if row == 0:
            cell.get_text().set_weight("bold")
    save(fig, 4)


def main() -> None:
    """Generate all four report previews."""
    ensure_directories()
    frame = read_cleaned_data()
    page_one(frame)
    page_two(frame)
    page_three(frame)
    page_four(frame)


if __name__ == "__main__":
    main()
