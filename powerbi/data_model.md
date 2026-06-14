# Power BI Data Model

This model uses the cleaned mandi dataset as a quote-level fact table and a
dedicated date dimension for reliable time intelligence. The source contains
736,711 records from 2023-06-06 through 2025-06-11 for Onion, Potato, Rice,
Tomato, and Wheat.

## Load the Fact Table

1. In Power BI Desktop, select **Get data > Text/CSV**.
2. Load `data/cleaned/mandi_cleaned_master.csv`.
3. In Power Query, rename the query to `MandiPrices`.
4. Apply the data types below and then select **Close & Apply**.

| Column | Power BI data type | Default summarization |
|---|---|---|
| `state` | Text | Do not summarize |
| `district` | Text | Do not summarize |
| `market` | Text | Do not summarize |
| `commodity` | Text | Do not summarize |
| `variety` | Text | Do not summarize |
| `grade` | Text | Do not summarize |
| `arrival_date` | Date | Do not summarize |
| `min_price` | Decimal number | Average |
| `max_price` | Decimal number | Average |
| `modal_price` | Decimal number | Average |
| `price_consistency_flag` | Whole number | Sum |
| `year` | Whole number | Do not summarize |
| `month_number` | Whole number | Do not summarize |
| `month` | Text | Do not summarize |
| `year_month` | Text | Do not summarize |
| `quarter` | Text | Do not summarize |
| `season` | Text | Do not summarize |
| `price_range` | Decimal number | Average |
| `rolling_30d_avg` | Decimal number | Average |
| `price_deviation_pct` | Decimal number | Average |
| `price_volatility_flag` | Whole number | Sum |
| `price_z_score` | Decimal number | Average |
| `anomaly_flag` | Whole number | Sum |

Set the format of all price fields to `English (India)` currency with no more
than two decimal places. Format `price_deviation_pct` as a decimal number
rather than Power BI percentage because the source already stores percentage
points, for example `30` means 30%.

The fact-table grain is one observed commodity quote for a market, variety,
grade, and arrival date. Do not remove rows in Power BI; all quality rules are
already applied by `scripts/data_cleaning.py`.

## Create the Date Table

Create a calculated table from **Table tools > New table**:

```DAX
DimDate =
VAR MinFactDate =
    MINX ( ALL ( MandiPrices ), MandiPrices[arrival_date] )
VAR MaxFactDate =
    MAXX ( ALL ( MandiPrices ), MandiPrices[arrival_date] )
RETURN
    ADDCOLUMNS (
        CALENDAR ( MinFactDate, MaxFactDate ),
        "Year", YEAR ( [Date] ),
        "Month Number", MONTH ( [Date] ),
        "Month", FORMAT ( [Date], "MMMM" ),
        "Year Month", FORMAT ( [Date], "YYYY-MM" ),
        "Year Month Sort", YEAR ( [Date] ) * 100 + MONTH ( [Date] ),
        "Quarter", "Q" & FORMAT ( [Date], "Q" ),
        "Season",
            SWITCH (
                TRUE (),
                MONTH ( [Date] ) IN { 7, 8, 9, 10 }, "Kharif",
                MONTH ( [Date] ) IN { 11, 12, 1, 2, 3 }, "Rabi",
                "Zaid"
            )
    )
```

Configure `DimDate` as follows:

- Mark it as the model's date table using `DimDate[Date]`.
- Sort `DimDate[Month]` by `DimDate[Month Number]`.
- Sort `DimDate[Year Month]` by `DimDate[Year Month Sort]`.
- Set `Date`, `Year`, `Month`, `Year Month`, `Quarter`, and `Season` to
  **Do not summarize**.
- Hide `Month Number` and `Year Month Sort` from report view after sorting.
- Disable **Auto date/time** for the current file to avoid hidden date tables.

The date table intentionally spans the observed data range. This keeps report
slicers focused on dates for which the project has source coverage.

## Relationship

Create this relationship in Model view:

| From | To | Cardinality | Cross-filter | Active |
|---|---|---|---|---|
| `DimDate[Date]` | `MandiPrices[arrival_date]` | One-to-many | Single | Yes |

`DimDate` is the one side and `MandiPrices` is the many side. Use fields from
`DimDate` for every date slicer and chart axis. Single-direction filtering
prevents ambiguous filter paths and lets the date dimension filter the fact
table predictably.

Do not create relationships from the derived date columns in `MandiPrices`
(`year`, `month`, `year_month`, or `quarter`). Hide those duplicate columns
from report view after validating the relationship. Keep `season` visible in
the fact table because it is a business classification used by existing SQL
and Python outputs; prefer `DimDate[Season]` for time-based visuals.

## Base Measures

Create a display folder named `01 Base Measures` and add these measures to
`MandiPrices`.

```DAX
Avg Modal Price =
AVERAGE ( MandiPrices[modal_price] )
```

Returns the mean modal price for the current date, commodity, state, market,
and slicer context. Format as `English (India)` currency with two decimals.

```DAX
Max Price Recorded =
MAX ( MandiPrices[max_price] )
```

Returns the highest quoted maximum price in the current filter context.
Format as `English (India)` currency with two decimals.

```DAX
Min Price Recorded =
MIN ( MandiPrices[min_price] )
```

Returns the lowest quoted minimum price in the current filter context. Format
as `English (India)` currency with two decimals.

```DAX
Total Market Entries =
COUNTROWS ( MandiPrices )
```

Counts quote records after all report filters. Format as a whole number with
the thousands separator enabled.

These are explicit measures, so report visuals should use them instead of
Power BI's implicit column aggregations.

## Field Organization

Use these display folders on `MandiPrices`:

| Display folder | Fields |
|---|---|
| `Geography` | `state`, `district`, `market` |
| `Commodity Details` | `commodity`, `variety`, `grade` |
| `Prices` | `min_price`, `max_price`, `modal_price`, `price_range`, `rolling_30d_avg` |
| `Quality Flags` | `price_consistency_flag`, `price_volatility_flag`, `anomaly_flag`, `price_deviation_pct`, `price_z_score` |
| `01 Base Measures` | The four measures defined above |

Set the data category for `state` to **State or Province** and `district` to
**County**. Set the data category for `market` to **Place**. This metadata
supports the India filled-map visual planned for the dashboard while retaining
the original text values.

## Validation Checklist

After applying the model, verify:

1. `MandiPrices` contains exactly 736,711 rows.
2. `DimDate` runs continuously from 2023-06-06 through 2025-06-11.
3. The relationship is active, one-to-many, and filters from `DimDate` to
   `MandiPrices`.
4. A table grouped by `DimDate[Year]` and `commodity` matches the annual SQL
   aggregations in `sql/query_results/08_year_over_year_price_change.csv`.
5. A card using `Total Market Entries` returns 736,711 with no filters.
6. Selecting a date slicer changes all four base measures.

The completed model is the foundation for the trend, comparison, seasonal,
and anomaly measures added in the next commit.
