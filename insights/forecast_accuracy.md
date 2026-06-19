# Forecast Accuracy

Prophet is evaluated with a chronological holdout containing up to 90 observed daily values, capped at 20% of each commodity's history with a 30-day minimum. This adaptive rule preserves enough training data for Tomato's shorter series. The target is the national daily median modal price, chosen to reduce the influence of isolated data-entry errors while preserving the market-level price signal.

| Commodity | MAE (INR/qtl) | RMSE (INR/qtl) | MAPE | Holdout observations | Holdout period |
|---|---:|---:|---:|---:|---|
| Onion | 1,274.95 | 1,350.87 | 86.52% | 90 | 2025-03-14 to 2025-06-11 |
| Tomato | 1,087.84 | 1,185.04 | 74.84% | 31 | 2023-10-07 to 2023-11-06 |

## Method

- Forecast horizon: 90 days.
- Features: Prophet trend, weekly seasonality, and multiplicative seasonal effects. Yearly seasonality is enabled only when at least 365 days of history are available.
- Validation: chronological holdout; no future observations are used to fit the evaluation model.
- Final forecasts: each model is refit on all available observations before generating future values.
- Intervals: exported lower and upper bounds are Prophet's 80% uncertainty interval.
- Coverage caveat: Tomato data ends on 2023-11-06, so its 90-day projection is a historical back-cast artifact relative to the full dataset and carries substantially more uncertainty than Onion.

These forecasts are analytical baselines, not trading advice. Weather, arrivals, policy changes, storage conditions, and market closures should be added before operational deployment.
