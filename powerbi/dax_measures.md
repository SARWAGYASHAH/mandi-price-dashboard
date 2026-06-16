# Power BI DAX Measures

Create these measures in the `MandiPrices` table after completing the model in
`powerbi/data_model.md`. Use `DimDate` fields for all date axes and slicers.

## 01 Base Measures

```DAX
// Mean modal price in the active report context.
Avg Modal Price =
AVERAGE ( MandiPrices[modal_price] )

// Highest quoted maximum price in the active report context.
Max Price Recorded =
MAX ( MandiPrices[max_price] )

// Lowest quoted minimum price in the active report context.
Min Price Recorded =
MIN ( MandiPrices[min_price] )

// Number of cleaned quote records after filters.
Total Market Entries =
COUNTROWS ( MandiPrices )
```

Format the three price measures as Indian rupee currency and the entry count
as a whole number.

## 02 Trend Measures

```DAX
// Percentage change from the preceding calendar month.
MoM Price Change % =
VAR PreviousMonthPrice =
    CALCULATE (
        [Avg Modal Price],
        DATEADD ( DimDate[Date], -1, MONTH )
    )
RETURN
    DIVIDE ( [Avg Modal Price] - PreviousMonthPrice, PreviousMonthPrice )

// Percentage change from the equivalent date period one year earlier.
YoY Price Change % =
VAR PreviousYearPrice =
    CALCULATE (
        [Avg Modal Price],
        DATEADD ( DimDate[Date], -1, YEAR )
    )
RETURN
    DIVIDE ( [Avg Modal Price] - PreviousYearPrice, PreviousYearPrice )

// Trailing 30-calendar-day mean ending at the latest visible date.
30 Day Rolling Average Price =
VAR LastVisibleDate = MAX ( DimDate[Date] )
RETURN
    CALCULATE (
        [Avg Modal Price],
        DATESINPERIOD ( DimDate[Date], LastVisibleDate, -30, DAY )
    )

// Relative dispersion of modal prices; higher values mean less stable prices.
Price Volatility Index =
DIVIDE (
    STDEV.P ( MandiPrices[modal_price] ),
    [Avg Modal Price]
)
```

Format all four as percentages except `30 Day Rolling Average Price`, which
uses Indian rupee currency. The volatility index is the coefficient of
variation, making crops with different price scales comparable.

## 03 Comparison Measures

```DAX
// Rank states from highest to lowest average modal price within active slicers.
State Rank by Avg Price =
RANKX (
    ALLSELECTED ( MandiPrices[state] ),
    [Avg Modal Price],
    ,
    DESC,
    DENSE
)

// Helper rank based on quote count. The source has no physical arrival-volume field.
Market Entry Rank =
RANKX (
    ALLSELECTED ( MandiPrices[market] ),
    [Total Market Entries],
    ,
    DESC,
    DENSE
)

// Return quote count only for the five most frequently reported markets.
Top 5 Markets by Volume =
IF ( [Market Entry Rank] <= 5, [Total Market Entries] )

// Return the lowest-average-price market in the selected commodity context.
Cheapest Market per Commodity =
VAR MarketPrices =
    ADDCOLUMNS (
        ALLSELECTED ( MandiPrices[market] ),
        "@Price", CALCULATE ( [Avg Modal Price] ),
        "@Entries", CALCULATE ( [Total Market Entries] )
    )
VAR Cheapest =
    TOPN ( 1, MarketPrices, [@Price], ASC, [@Entries], DESC, MandiPrices[market], ASC )
RETURN
    CONCATENATEX (
        Cheapest,
        MandiPrices[market] & " | " & FORMAT ( [@Price], "₹#,##0.00" ),
        ""
    )

// Return the highest-average-price market in the selected commodity context.
Most Expensive Market per Commodity =
VAR MarketPrices =
    ADDCOLUMNS (
        ALLSELECTED ( MandiPrices[market] ),
        "@Price", CALCULATE ( [Avg Modal Price] ),
        "@Entries", CALCULATE ( [Total Market Entries] )
    )
VAR MostExpensive =
    TOPN ( 1, MarketPrices, [@Price], DESC, [@Entries], DESC, MandiPrices[market], ASC )
RETURN
    CONCATENATEX (
        MostExpensive,
        MandiPrices[market] & " | " & FORMAT ( [@Price], "₹#,##0.00" ),
        ""
    )
```

`Top 5 Markets by Volume` uses reporting frequency as a volume proxy because
the supplied dataset has no arrivals quantity column. State and commodity
slicers remain active in the cheapest and most-expensive market measures.

## 04 Seasonal Measures

```DAX
// Average price under the season filter used by a row, legend, or slicer.
Season wise Avg Price =
[Avg Modal Price]

// Name and average price of the highest-priced visible month.
Peak Price Month per Commodity =
VAR MonthPrices =
    ADDCOLUMNS (
        ALLSELECTED ( DimDate[Month], DimDate[Month Number] ),
        "@Price", CALCULATE ( [Avg Modal Price] )
    )
VAR PeakMonth =
    TOPN ( 1, FILTER ( MonthPrices, NOT ISBLANK ( [@Price] ) ), [@Price], DESC, DimDate[Month Number], ASC )
RETURN
    CONCATENATEX (
        PeakMonth,
        DimDate[Month] & " | " & FORMAT ( [@Price], "₹#,##0.00" ),
        ""
    )

// Name and average price of the lowest-priced visible month.
Lowest Price Month per Commodity =
VAR MonthPrices =
    ADDCOLUMNS (
        ALLSELECTED ( DimDate[Month], DimDate[Month Number] ),
        "@Price", CALCULATE ( [Avg Modal Price] )
    )
VAR LowestMonth =
    TOPN ( 1, FILTER ( MonthPrices, NOT ISBLANK ( [@Price] ) ), [@Price], ASC, DimDate[Month Number], ASC )
RETURN
    CONCATENATEX (
        LowestMonth,
        DimDate[Month] & " | " & FORMAT ( [@Price], "₹#,##0.00" ),
        ""
    )
```

Use `Season wise Avg Price` with `DimDate[Season]`. The peak and lowest month
measures retain commodity, state, market, and visible date-range filters.

## 05 Anomaly Measures

```DAX
// Count records that breach the commodity-level two-standard-deviation rule.
Total Anomaly Count =
CALCULATE (
    COUNTROWS ( MandiPrices ),
    MandiPrices[anomaly_flag] = 1
)

// Within-state anomaly rate when state is on the visual axis.
Anomaly % by State =
DIVIDE ( [Total Anomaly Count], [Total Market Entries] )

// Within-commodity anomaly rate when commodity is on the visual axis.
Anomaly % by Commodity =
DIVIDE ( [Total Anomaly Count], [Total Market Entries] )
```

Format both anomaly-rate measures as percentages. The numerator and
denominator inherit the row context, so each visual shows a within-group rate
rather than that group's share of all anomalies.

## Validation

With no filters, verify these values:

| Measure | Expected result |
|---|---:|
| `Avg Modal Price` | INR 2,474.96 |
| `Total Market Entries` | 736,711 |
| `Total Anomaly Count` | 16,336 |
| Overall anomaly rate | 2.22% |

Monthly and yearly measures return blank where no valid comparison period is
available. This is expected and preferable to displaying an invented zero.
