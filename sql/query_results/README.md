# SQL Query Results

These files contain the exported results of the eight analyses in
`sql/queries.sql`. They were generated from 736,711 cleaned mandi price
records covering 2023-06-06 through 2025-06-11.

## Export Inventory

| File | Rows | Analysis |
|---|---:|---|
| `01_state_commodity_avg_prices.csv` | 102 | Average modal price by state and commodity |
| `02_top_10_expensive_markets.csv` | 10 | Markets with the highest average modal price |
| `03_bottom_10_cheapest_markets.csv` | 10 | Markets with the lowest average modal price |
| `04_monthly_price_aggregation.csv` | 67 | Monthly crop price trends |
| `05_season_price_comparison.csv` | 13 | Commodity price comparison by crop season |
| `06_anomaly_flagged_records.csv` | 16,336 | Records flagged by the two-standard-deviation rule |
| `07_state_price_rankings.csv` | 102 | State price ranks within each commodity |
| `08_year_over_year_price_change.csv` | 10 | Annual price change by commodity |

## Market Price Leaders

The highest average-price market is Patna (Musallahpur), Bihar, at INR
44,409.68 per quintal across 31 entries. The next two are Sohra, Meghalaya,
at INR 26,908.35 across 37 entries and Pothencode, Kerala, at INR 24,425.29
across 919 entries.

The lowest average-price market is Raikot, Punjab, at INR 341.72 per quintal
across 29 entries. It is followed by Suragana, Maharashtra, at INR 442.00
from one entry and Janata Agri Market, Maharashtra, at INR 450.00 from one
entry.

## Highest-Priced State by Commodity

| Commodity | State | Average modal price | Entries |
|---|---|---:|---:|
| Onion | Nagaland | INR 5,054.16 | 757 |
| Potato | Tamil Nadu | INR 4,552.11 | 35,785 |
| Rice | Delhi | INR 5,525.33 | 18 |
| Tomato | Meghalaya | INR 9,588.73 | 71 |
| Wheat | Kerala | INR 4,400.00 | 4 |

## Interpretation Notes

- Market and state rankings use all available records and do not apply a
  minimum observation threshold. Review `market_entries` before using a rank
  for operational decisions.
- Known state-name variants are canonicalized by the cleaning pipeline before
  ranking, preventing labels such as `Tamil Nadu` and `Tamilnadu` from
  appearing as separate regions.
- Statistical anomaly flags identify observations for investigation; they do
  not establish data error, manipulation, or a causal event.
- Partial-year results should not be treated as directly comparable with a
  complete calendar year without accounting for coverage.
