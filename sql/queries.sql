-- Indian Agricultural Mandi Price Analysis
-- Run from the repository root with:
--   sqlite3 -batch data/mandi_prices.db ".read sql/queries.sql"
--
-- The script creates data/mandi_prices.db, imports the cleaned CSV, applies
-- appropriate SQLite data types, and then runs the required analysis queries.

.bail on

DROP TABLE IF EXISTS mandi_prices;
DROP TABLE IF EXISTS mandi_prices_import;

-- Import into a text staging table first so blank CSV values can be converted
-- to SQL NULL values while loading the final typed analytics table.
CREATE TABLE mandi_prices_import (
    state TEXT,
    district TEXT,
    market TEXT,
    commodity TEXT,
    variety TEXT,
    grade TEXT,
    arrival_date TEXT,
    min_price TEXT,
    max_price TEXT,
    modal_price TEXT,
    price_consistency_flag TEXT,
    year TEXT,
    month_number TEXT,
    month TEXT,
    year_month TEXT,
    quarter TEXT,
    season TEXT,
    price_range TEXT,
    rolling_30d_avg TEXT,
    price_deviation_pct TEXT,
    price_volatility_flag TEXT,
    price_z_score TEXT,
    anomaly_flag TEXT
);

.mode csv
.import --skip 1 data/cleaned/mandi_cleaned_master.csv mandi_prices_import

CREATE TABLE mandi_prices (
    price_record_id INTEGER PRIMARY KEY,
    state TEXT NOT NULL,
    district TEXT NOT NULL,
    market TEXT NOT NULL,
    commodity TEXT NOT NULL,
    variety TEXT,
    grade TEXT,
    arrival_date TEXT NOT NULL,
    min_price REAL,
    max_price REAL,
    modal_price REAL NOT NULL,
    price_consistency_flag INTEGER NOT NULL DEFAULT 0 CHECK (price_consistency_flag IN (0, 1)),
    year INTEGER NOT NULL,
    month_number INTEGER NOT NULL CHECK (month_number BETWEEN 1 AND 12),
    month TEXT NOT NULL,
    year_month TEXT NOT NULL,
    quarter TEXT NOT NULL CHECK (quarter IN ('Q1', 'Q2', 'Q3', 'Q4')),
    season TEXT NOT NULL CHECK (season IN ('Kharif', 'Rabi', 'Zaid')),
    price_range REAL,
    rolling_30d_avg REAL,
    price_deviation_pct REAL,
    price_volatility_flag INTEGER NOT NULL DEFAULT 0 CHECK (price_volatility_flag IN (0, 1)),
    price_z_score REAL,
    anomaly_flag INTEGER NOT NULL DEFAULT 0 CHECK (anomaly_flag IN (0, 1))
);

INSERT INTO mandi_prices (
    state,
    district,
    market,
    commodity,
    variety,
    grade,
    arrival_date,
    min_price,
    max_price,
    modal_price,
    price_consistency_flag,
    year,
    month_number,
    month,
    year_month,
    quarter,
    season,
    price_range,
    rolling_30d_avg,
    price_deviation_pct,
    price_volatility_flag,
    price_z_score,
    anomaly_flag
)
SELECT
    NULLIF(TRIM(state), ''),
    NULLIF(TRIM(district), ''),
    NULLIF(TRIM(market), ''),
    NULLIF(TRIM(commodity), ''),
    NULLIF(TRIM(variety), ''),
    NULLIF(TRIM(grade), ''),
    NULLIF(TRIM(arrival_date), ''),
    CAST(NULLIF(TRIM(min_price), '') AS REAL),
    CAST(NULLIF(TRIM(max_price), '') AS REAL),
    CAST(NULLIF(TRIM(modal_price), '') AS REAL),
    CAST(COALESCE(NULLIF(TRIM(price_consistency_flag), ''), '0') AS INTEGER),
    CAST(NULLIF(TRIM(year), '') AS INTEGER),
    CAST(NULLIF(TRIM(month_number), '') AS INTEGER),
    NULLIF(TRIM(month), ''),
    NULLIF(TRIM(year_month), ''),
    NULLIF(TRIM(quarter), ''),
    NULLIF(TRIM(season), ''),
    CAST(NULLIF(TRIM(price_range), '') AS REAL),
    CAST(NULLIF(TRIM(rolling_30d_avg), '') AS REAL),
    CAST(NULLIF(TRIM(price_deviation_pct), '') AS REAL),
    CAST(COALESCE(NULLIF(TRIM(price_volatility_flag), ''), '0') AS INTEGER),
    CAST(NULLIF(TRIM(price_z_score), '') AS REAL),
    CAST(COALESCE(NULLIF(TRIM(anomaly_flag), ''), '0') AS INTEGER)
FROM mandi_prices_import;

DROP TABLE mandi_prices_import;

-- These indexes support the dimensions and filters used repeatedly below.
CREATE INDEX idx_mandi_commodity_date
    ON mandi_prices (commodity, arrival_date);
CREATE INDEX idx_mandi_state_commodity
    ON mandi_prices (state, commodity);
CREATE INDEX idx_mandi_market
    ON mandi_prices (market);
CREATE INDEX idx_mandi_season
    ON mandi_prices (season);
CREATE INDEX idx_mandi_anomaly
    ON mandi_prices (anomaly_flag);

ANALYZE;

.headers on
.mode column

-- Query 1: Compare typical commodity prices across states to identify regional
-- price differences and support state-level sourcing or policy decisions.
SELECT
    state,
    commodity,
    ROUND(AVG(modal_price), 2) AS avg_modal_price,
    COUNT(*) AS market_entries
FROM mandi_prices
GROUP BY state, commodity
ORDER BY commodity, avg_modal_price DESC, state;

-- Query 2: Identify the ten markets with the highest average modal prices,
-- highlighting expensive trading locations and possible supply constraints.
SELECT
    state,
    district,
    market,
    ROUND(AVG(modal_price), 2) AS avg_modal_price,
    COUNT(*) AS market_entries
FROM mandi_prices
GROUP BY state, district, market
ORDER BY avg_modal_price DESC, market_entries DESC, market
LIMIT 10;

-- Query 3: Identify the ten markets with the lowest average modal prices,
-- revealing lower-cost sourcing opportunities across the mandi network.
SELECT
    state,
    district,
    market,
    ROUND(AVG(modal_price), 2) AS avg_modal_price,
    COUNT(*) AS market_entries
FROM mandi_prices
GROUP BY state, district, market
ORDER BY avg_modal_price ASC, market_entries DESC, market
LIMIT 10;

-- Query 4: Summarize monthly crop prices to expose time trends and provide the
-- grain needed for month-over-month analysis in reporting tools.
SELECT
    commodity,
    year,
    month_number,
    month,
    year_month,
    ROUND(AVG(min_price), 2) AS avg_min_price,
    ROUND(AVG(max_price), 2) AS avg_max_price,
    ROUND(AVG(modal_price), 2) AS avg_modal_price,
    ROUND(MIN(modal_price), 2) AS lowest_modal_price,
    ROUND(MAX(modal_price), 2) AS highest_modal_price,
    COUNT(*) AS market_entries
FROM mandi_prices
GROUP BY commodity, year, month_number, month, year_month
ORDER BY commodity, year, month_number;

-- Query 5: Compare prices by agricultural season to show how crop cycles and
-- seasonal supply patterns affect modal prices for each commodity.
SELECT
    commodity,
    season,
    ROUND(AVG(modal_price), 2) AS avg_modal_price,
    ROUND(AVG(price_range), 2) AS avg_price_range,
    COUNT(*) AS market_entries
FROM mandi_prices
GROUP BY commodity, season
ORDER BY commodity, avg_modal_price DESC;

-- Query 6: Return every statistically flagged price record for investigation
-- of unusual spikes, drops, data-quality issues, or market manipulation risks.
SELECT
    arrival_date,
    state,
    district,
    market,
    commodity,
    variety,
    min_price,
    max_price,
    modal_price,
    ROUND(rolling_30d_avg, 2) AS rolling_30d_avg,
    ROUND(price_deviation_pct, 2) AS price_deviation_pct,
    ROUND(price_z_score, 4) AS price_z_score
FROM mandi_prices
WHERE anomaly_flag = 1
ORDER BY ABS(price_z_score) DESC, arrival_date DESC;

-- Query 7: Rank states within each commodity by average modal price so users
-- can compare relative price positions without larger-value crops dominating.
WITH state_prices AS (
    SELECT
        commodity,
        state,
        AVG(modal_price) AS avg_modal_price,
        COUNT(*) AS market_entries
    FROM mandi_prices
    GROUP BY commodity, state
)
SELECT
    commodity,
    state,
    ROUND(avg_modal_price, 2) AS avg_modal_price,
    market_entries,
    DENSE_RANK() OVER (
        PARTITION BY commodity
        ORDER BY avg_modal_price DESC
    ) AS state_price_rank
FROM state_prices
ORDER BY commodity, state_price_rank, state;

-- Query 8: Calculate year-over-year average price movement per commodity to
-- quantify long-term inflation, deflation, and major shifts in mandi pricing.
WITH yearly_prices AS (
    SELECT
        commodity,
        year,
        AVG(modal_price) AS avg_modal_price
    FROM mandi_prices
    GROUP BY commodity, year
),
prices_with_previous_year AS (
    SELECT
        commodity,
        year,
        avg_modal_price,
        LAG(avg_modal_price) OVER (
            PARTITION BY commodity
            ORDER BY year
        ) AS previous_year_avg_price
    FROM yearly_prices
)
SELECT
    commodity,
    year,
    ROUND(avg_modal_price, 2) AS avg_modal_price,
    ROUND(previous_year_avg_price, 2) AS previous_year_avg_price,
    ROUND(
        100.0 * (avg_modal_price - previous_year_avg_price)
        / NULLIF(previous_year_avg_price, 0),
        2
    ) AS yoy_price_change_pct
FROM prices_with_previous_year
ORDER BY commodity, year;
