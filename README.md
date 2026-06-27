# 🌾 Indian Agricultural Mandi Price Intelligence

An interview-ready analytics portfolio that turns **736,711** Indian mandi price
quotes into a reproducible Python and SQLite pipeline, a documented four-page
Power BI report, anomaly investigations, Prophet forecasts, automated
plain-English insights, and a responsive multi-page project website — with a
**daily auto-update pipeline** powered by GitHub Actions and the data.gov.in API.

<p align="center">
  <a href="https://sarwagyashah.github.io/mandi-price-dashboard/"><strong>🔗 View Live Website</strong></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/SARWAGYASHAH/mandi-price-dashboard"><strong>📂 View Repository</strong></a>
</p>

---

![National Overview](powerbi/dashboard_screenshots/page1.png)

## 📌 Problem Statement

Agricultural price quotes vary across crops, markets, states, seasons,
varieties, grades, and reporting practices. This project answers four practical
questions:

1. Which crops, states, and markets are relatively expensive or cheap?
2. How do prices move over time and across crop seasons?
3. Which records are statistically unusual enough to investigate?
4. How well can a baseline time-series model forecast Onion and Tomato prices?

## 📊 Dataset

The supplied master CSV is `data/raw/Agriculture_price_dataset.csv`. It
contains State, District, Market, Commodity, Variety, Grade, Price Date,
Min Price, Max Price, and Modal Price. Only **Onion, Tomato, Potato, Wheat, and
Rice** are retained.

**Live data** is fetched daily from the [data.gov.in](https://data.gov.in)
Open Government Data API (resource `9ef84268-d588-465a-a308-a864a43d0070`)
via `scripts/fetch_live_data.py`. The script uses incremental watermarking to
download only new records since the last successful run.

### Cleaned Coverage

| Metric | Value |
|---|---:|
| Valid quote records | 736,711 |
| Date range | 6 June 2023 to 11 June 2025 |
| Commodities | 5 |
| Canonical states / union territories | 26 |
| Distinct market labels | 1,597 |
| Statistical anomaly flags | 16,336 (2.22%) |

## 🛠️ Tools & Technologies

| Tool | Purpose |
|---|---|
| **Python** | pandas, NumPy, Matplotlib, scikit-learn for data processing |
| **Prophet** | Time-series forecasting with weekly and yearly seasonality |
| **SQLite** | Structured queries, rankings, and reproducible CSV exports |
| **Power BI** | Star schema, 18 DAX measures, 4-page interactive dashboard |
| **HTML/CSS/JS** | 5-page responsive website with WebGL shader background |
| **GitHub Pages** | Live deployment of the project portfolio website |
| **GitHub Actions** | Daily automated data refresh and pipeline execution |

## 📁 Project Structure

```text
mandi-price-dashboard/
├── .github/
│   └── workflows/
│       └── daily_update.yml          # Daily auto-update pipeline
├── data/
│   ├── raw/Agriculture_price_dataset.csv
│   ├── cleaned/
│   │   ├── mandi_cleaned_master.csv
│   │   └── cleaning_report.json
│   ├── outputs/
│   │   ├── anomaly_report.csv
│   │   ├── onion_forecast.csv
│   │   └── tomato_forecast.csv
│   ├── ingestion_metadata.json       # Watermark for incremental fetches
│   └── mandi_prices.db
├── scripts/
│   ├── common.py                     # Shared constants and paths
│   ├── data_cleaning.py              # Task 1: Clean and derive features
│   ├── anomaly_detection.py          # Task 6: 2σ anomaly flagging
│   ├── forecast_model.py             # Task 5: Prophet forecasts
│   ├── automated_insights.py         # Task 7: Plain English insights
│   ├── generate_dashboard_previews.py # Matplotlib dashboard PNGs
│   ├── fetch_live_data.py            # Live data from data.gov.in API
│   └── run_pipeline.py               # One-command pipeline orchestrator
├── sql/
│   ├── queries.sql
│   └── query_results/
│       ├── 01_state_commodity_avg_prices.csv
│       ├── 02_top_10_expensive_markets.csv
│       ├── 03_bottom_10_cheapest_markets.csv
│       ├── 04_monthly_crop_aggregation.csv
│       ├── 05_season_wise_comparison.csv
│       ├── 06_anomaly_flagged_records.csv
│       ├── 07_state_price_rankings.csv
│       ├── 08_yoy_price_change.csv
│       └── README.md
├── powerbi/
│   ├── data_model.md
│   ├── dax_measures.md
│   ├── dashboard_blueprint.md
│   └── dashboard_screenshots/
│       ├── page1.png
│       ├── page2.png
│       ├── page3.png
│       └── page4.png
├── visuals/
│   ├── onion_forecast.png
│   └── tomato_forecast.png
├── insights/
│   ├── anomaly_summary.md
│   ├── automated_insights.txt
│   ├── forecast_accuracy.md
│   └── key_findings.md
├── docs/
│   ├── index.html
│   ├── dashboard.html
│   ├── insights.html
│   ├── forecast.html
│   ├── about.html
│   ├── shared.css
│   ├── shared.js
│   └── assets/
├── requirements.txt
└── README.md
```

## 🔬 Methodology

### 1. Data Cleaning

`scripts/data_cleaning.py` standardizes headers, filters the five target crops,
parses dates and prices, removes non-positive and internally invalid ranges,
deduplicates records, and canonicalizes known geography variants such as
`Tamilnadu` to `Tamil Nadu` and `Orissa` to `Odisha`.

**Missing-data policy:**

- Critical geography, date, commodity, and price values are required.
- Blank Variety and Grade values become `Unknown`.
- Non-positive prices and rows where maximum is below minimum are removed.
- Modal prices outside the stated minimum-to-maximum range are retained and
  flagged because they may be either source errors or genuine unusual quotes.

Derived features include Year, Month, Quarter, Season, Price Range, a
market-level 30-day rolling average, a 30% volatility flag, commodity z-score,
and a two-standard-deviation anomaly flag. Exact row decisions are written to
`data/cleaned/cleaning_report.json`.

### 2. SQL Layer

`sql/queries.sql` imports the cleaned CSV through a text staging table, creates
a typed and indexed `mandi_prices` table, and exports eight result sets:

| Query | Output |
|---|---|
| State and commodity average prices | `01_state_commodity_avg_prices.csv` |
| Top 10 most expensive markets | `02_top_10_expensive_markets.csv` |
| Bottom 10 cheapest markets | `03_bottom_10_cheapest_markets.csv` |
| Monthly crop aggregation | `04_monthly_crop_aggregation.csv` |
| Season-wise comparison | `05_season_wise_comparison.csv` |
| Anomaly flagged records | `06_anomaly_flagged_records.csv` |
| State price rankings | `07_state_price_rankings.csv` |
| Year-over-year commodity change | `08_yoy_price_change.csv` |

### 3. Power BI

The report uses `MandiPrices` as a quote-level fact table and `DimDate` as an
active one-to-many date dimension. 18 DAX measures are organized across five
categories: Basic, Trend, Comparison, Seasonal, and Anomaly.

The complete model, DAX, formatting, interactions, and exact four-page visual
inventory are documented in `powerbi/`.

The committed PNGs are data-backed build previews generated with Matplotlib.
They are not presented as a `.pbix` export.

### 4. Anomaly Detection

Each modal price is compared with its commodity mean and standard deviation.
A z-score above 2 is a **High Price Spike** and below −2 is a **Low Price
Drop**.

| Metric | Value |
|---|---:|
| Records analysed | 736,711 |
| Records flagged | 16,336 (2.22%) |
| High price spikes | 16,204 |
| Low price drops | 132 |
| Commodity with most anomalies | Potato (9,646) |
| State with most anomalies | Tamil Nadu (9,085) |
| Month with most anomalies | November (3,428) |
| Highest spike | Onion at Jehanabad, Bihar — INR 460,000 (z = 196.13) |
| Lowest drop | Wheat at Shamshabad, MP — INR 215 (z = −7.63) |

A flag is an investigation signal, not evidence of manipulation. Arrival
quantity, grade, weather, trader, auction, and enforcement data are required
for causal or misconduct claims.

Full anomaly breakdown: [insights/anomaly_summary.md](insights/anomaly_summary.md)

### 5. Forecasting

Onion and Tomato quotes are aggregated to a national daily median. Prophet
uses weekly seasonality and multiplicative seasonal effects; yearly
seasonality is enabled only where at least 365 days of history exist.

Evaluation uses a chronological holdout of up to 90 observed days, capped at
20% of the series with a 30-day minimum. No future holdout observations are
used to fill training gaps.

| Commodity | MAE (INR/qtl) | RMSE (INR/qtl) | MAPE | Holdout | Period |
|---|---:|---:|---:|---:|---|
| Onion | 1,274.95 | 1,350.87 | 86.52% | 90 obs | 2025-03-14 to 2025-06-11 |
| Tomato | 1,087.84 | 1,185.04 | 74.84% | 31 obs | 2023-10-07 to 2023-11-06 |

The errors are high, so these forecasts are transparent analytical baselines,
not operational trading models. Tomato observations end on 6 November 2023;
its exported forecast is therefore a historical modeling artifact relative to
the full dataset.

Full methodology: [insights/forecast_accuracy.md](insights/forecast_accuracy.md)

#### Onion — 90 Day Forecast

![Onion Forecast](visuals/onion_forecast.png)

#### Tomato — 90 Day Forecast

![Tomato Forecast](visuals/tomato_forecast.png)

### 6. Automated Insights

`scripts/automated_insights.py` generates plain English summaries covering:

- Top price spike with date, state, and percentage deviation
- Most volatile crop with coefficient of variation
- Cheapest state for each commodity
- Most expensive market overall
- Seasonal pattern summary
- Anomaly count summary

Output: [insights/automated_insights.txt](insights/automated_insights.txt)

## 🔑 Key Findings

1. **Onion is the most volatile crop:** coefficient of variation is 83.81%.
2. **Seasonality is strongest for Tomato:** Kharif average price is 193.7%
   above Rabi.
3. **Low-cost sourcing is crop-specific:** Madhya Pradesh is cheapest for
   Onion and Tomato among states with at least 30 quotes, while Punjab is
   cheapest for Potato.
4. **Extreme market gaps require validation:** Patna (Musallahpur) averages
   INR 44,409.68 across 31 records, far above the overall INR 2,474.96 average.
5. **Quality and anomaly checks converge:** 16,336 statistical flags and 1,246
   modal prices outside their stated range identify focused audit priorities.

Detailed interpretation: [insights/key_findings.md](insights/key_findings.md)

## 📈 Dashboard Pages

| Page | Purpose |
|---|---|
| National Overview | KPIs, crop trends, seasonality, and anomaly mix |
| State Wise Comparison | India filled map, state ranking, and reporting coverage |
| Crop Deep Dive | Rolling trend, seasonal profile, and market comparison |
| Market Intelligence | Anomaly concentration and record-level investigation |

### Page 1 — National Overview

![National Overview](powerbi/dashboard_screenshots/page1.png)

### Page 2 — State Wise Comparison + India Map

![State Wise Comparison](powerbi/dashboard_screenshots/page2.png)

### Page 3 — Crop Deep Dive

![Crop Deep Dive](powerbi/dashboard_screenshots/page3.png)

### Page 4 — Market Intelligence + Anomaly Flags

![Market Intelligence](powerbi/dashboard_screenshots/page4.png)

## 🌐 Project Website

The project includes a 5-page responsive portfolio website deployed on GitHub Pages:

| Page | Description |
|---|---|
| **Home** | Hero section, metrics counters, problem statement, toolchain, and key findings |
| **Dashboard** | All four Power BI page previews with DAX measure summaries and data model |
| **Insights** | Key findings cards, automated terminal-style insights, anomaly tables |
| **Forecast** | Prophet methodology pipeline, forecast charts with error metrics |
| **About** | Architecture, technology stack, project structure, methodology, and author |

**Design features:**
- WebGL shader animated background with saffron, teal, and blue orbs
- Glassmorphism dark theme with frosted-glass panels
- Animated counters, scroll-reveal transitions, and hover effects
- Fully responsive with mobile hamburger menu
- Inter + JetBrains Mono typography

## 🔄 Live Data Pipeline

The project includes a fully automated daily update system:

```
GitHub Actions (daily_update.yml)
  ├── fetch_live_data.py    → Pull new prices from data.gov.in API
  ├── data_cleaning.py      → Clean and add derived features
  ├── queries.sql            → Refresh SQL aggregations
  ├── anomaly_detection.py  → Re-run anomaly flagging
  ├── forecast_model.py     → Update Prophet forecasts
  ├── automated_insights.py → Regenerate English summaries
  └── generate_dashboard_previews.py → Rebuild dashboard PNGs
```

**Schedule:** Runs daily at 12:00 PM IST (6:30 AM UTC) via cron.

**Incremental ingestion:** A watermark file (`data/ingestion_metadata.json`)
tracks the last successfully fetched date. Each run downloads only new data
since the watermark — no redundant re-downloads.

**Manual trigger:** The workflow supports `workflow_dispatch` with options for:
- `days_back` — fetch the last N days
- `full_refresh` — re-download up to 365 days of history

**Graceful fallback:** If `DATA_GOV_API_KEY` is not set, the pipeline skips
the live fetch and re-processes existing data.

## 🚀 Run the Project

Prerequisites: Python 3.11 or newer, pip, and the SQLite command-line shell.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/run_pipeline.py
```

Manual execution:

```bash
python scripts/data_cleaning.py
sqlite3 -batch data/mandi_prices.db ".read sql/queries.sql"
python scripts/anomaly_detection.py
python scripts/forecast_model.py
python scripts/automated_insights.py
python scripts/generate_dashboard_previews.py
```

### Live data (optional)

To fetch fresh prices locally, register a free API key at
[data.gov.in](https://data.gov.in) and set it as an environment variable:

```bash
export DATA_GOV_API_KEY="your_key_here"
python scripts/fetch_live_data.py --days-back 7
```

For the GitHub Actions daily pipeline, add the key as a repository secret
named `DATA_GOV_API_KEY` under **Settings → Secrets → Actions**.

The dashboard preview generator downloads the India state-boundary GeoJSON
published by the [DataMeet maps project](https://github.com/datameet/maps) at
runtime. The website assets are copies of generated previews and forecasts.

To preview the website:

```bash
cd docs
python -m http.server 8000
```

Open `http://localhost:8000`.

## 👤 Author

**Sarwagya Shah**

- GitHub: [SARWAGYASHAH](https://github.com/SARWAGYASHAH)
- Repository: [mandi-price-dashboard](https://github.com/SARWAGYASHAH/mandi-price-dashboard)
