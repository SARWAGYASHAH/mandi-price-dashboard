# Power BI Dashboard Blueprint

## Report-Wide Design

- Canvas: 16:9, 1280 x 720.
- Theme: deep navy `#081B29`, slate `#102A3A`, off-white `#F5F7F2`,
  saffron `#F4A261`, green `#2A9D8F`, red `#E76F51`.
- Typography: Segoe UI Semibold for headings and Segoe UI for labels.
- Global slicers: `DimDate[Date]`, `MandiPrices[commodity]`,
  `MandiPrices[state]`, and `DimDate[Season]`.
- Add a reset-filters bookmark and synchronize the commodity, state, and date
  slicers across all pages.
- Tooltips should always show quote count alongside price so small samples are
  visible to the reader.

## Page 1 - National Overview

Purpose: give an executive summary of price level, coverage, trend, and risk.

| Visual | Fields and measures |
|---|---|
| KPI card | `Avg Modal Price` |
| KPI card | `Max Price Recorded` |
| KPI card | `Min Price Recorded` |
| KPI card | `Total Market Entries` |
| KPI card | `Total Anomaly Count` |
| Multi-line chart | Axis: `DimDate[Year Month]`; legend: `commodity`; value: `Avg Modal Price` |
| Clustered column chart | Axis: `commodity`; value: `Avg Modal Price`; tooltip: `Total Market Entries`, `Price Volatility Index` |
| Donut chart | Legend: `commodity`; value: `Total Anomaly Count` |
| Matrix | Rows: `commodity`; columns: `DimDate[Season]`; values: `Season wise Avg Price`, `Total Market Entries` |
| Smart narrative | Summarize `MoM Price Change %`, `YoY Price Change %`, and anomaly count |

Slicers: date range, commodity, season. Use saffron for selected price series,
green for stable values, and red only for anomaly indicators.

## Page 2 - State Wise Comparison + India Map

Purpose: reveal regional price differences and support state benchmarking.

| Visual | Fields and measures |
|---|---|
| India Filled Map | Location: `state`; color saturation: `Avg Modal Price`; tooltip: `State Rank by Avg Price`, `Total Market Entries`, `Anomaly % by State` |
| Ranked horizontal bar | Axis: `state`; value: `Avg Modal Price`; visual-level Top N: 10 |
| Scatter plot | X: `Total Market Entries`; Y: `Avg Modal Price`; details: `state`; size: `Total Anomaly Count`; legend: `commodity` |
| Matrix | Rows: `state`; columns: `commodity`; values: `Avg Modal Price`, `State Rank by Avg Price` |
| KPI card | Selected state's `State Rank by Avg Price` |
| KPI card | Selected state's `Anomaly % by State` |

Slicers: commodity, date range, season. Configure the filled map with a
sequential light-cream-to-dark-saffron scale: light means cheaper and dark
means more expensive. Set `state` data category to **State or Province** and
the map country context to India. Keep quote count in every tooltip to expose
thin samples.

## Page 3 - Crop Deep Dive

Purpose: let an analyst investigate one crop's trend, seasonality, volatility,
and market extremes.

| Visual | Fields and measures |
|---|---|
| Commodity button slicer | `commodity`; single select |
| Line chart | Axis: `DimDate[Date]`; values: `Avg Modal Price`, `30 Day Rolling Average Price` |
| KPI card | `MoM Price Change %` |
| KPI card | `YoY Price Change %` |
| KPI card | `Price Volatility Index` |
| KPI card | `Peak Price Month per Commodity` |
| KPI card | `Lowest Price Month per Commodity` |
| Clustered column chart | Axis: `DimDate[Season]`; values: `Season wise Avg Price` |
| Box-and-whisker custom visual | Category: `state`; samples: `modal_price` |
| Market comparison bar | Axis: `market`; value: `Avg Modal Price`; Top N: 10 by `Total Market Entries` |
| Text cards | `Cheapest Market per Commodity`; `Most Expensive Market per Commodity` |

Slicers: commodity, state, variety, grade, date range. Use the selected crop's
accent color consistently and keep the rolling average as a high-contrast
white line.

## Page 4 - Market Intelligence + Anomaly Flags

Purpose: surface unusual quotes, high-risk locations, and investigation leads.

| Visual | Fields and measures |
|---|---|
| KPI card | `Total Anomaly Count` |
| KPI card | `Anomaly % by Commodity` |
| KPI card | Sum of `price_volatility_flag` |
| Ranked bar | Axis: `state`; value: `Total Anomaly Count`; tooltip: `Anomaly % by State` |
| Ranked bar | Axis: `commodity`; value: `Total Anomaly Count`; tooltip: `Anomaly % by Commodity` |
| Scatter plot | X: `rolling_30d_avg`; Y: `modal_price`; details: market/date; legend: `anomaly_flag`; tooltip: `price_z_score`, `price_deviation_pct` |
| Detail table | `arrival_date`, `state`, `district`, `market`, `commodity`, `variety`, `modal_price`, `rolling_30d_avg`, `price_z_score`, `anomaly_flag` |
| Top markets bar | Axis: `market`; value: `Top 5 Markets by Volume` |

Slicers: anomaly flag, volatility flag, commodity, state, date range. Apply
conditional formatting to the table: red for `anomaly_flag = 1`, amber for
`price_volatility_flag = 1`, and neutral slate otherwise. Add a tooltip note:
"A statistical flag is a review signal, not proof of manipulation."

## Interaction Rules

1. The India map filters every visual on Page 2.
2. Commodity selection on Page 3 is single-select and required.
3. Anomaly bars cross-filter the Page 4 detail table.
4. Trend charts use `DimDate`, never the fact table's text month fields.
5. Disable interactions from KPI cards to prevent accidental filtering.
