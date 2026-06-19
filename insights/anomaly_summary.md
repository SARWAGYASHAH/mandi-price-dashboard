# Anomaly Detection Summary

## Method

Each quote is compared with its commodity mean. A record is flagged when its modal price is more than 2 standard deviations above or below that mean. Commodity-level thresholds keep crops with different normal price ranges comparable.

A statistical flag is a review signal, not proof of manipulation. Confirm flags against arrivals, grade, weather, holidays, and neighboring markets.

## Overall Results

- Records analysed: **736,711**.
- Records flagged: **16,336** (2.22%).
- Commodity with the most anomalies: **Potato** (9,646).
- State with the most anomalies: **Tamil Nadu** (9,085).
- Month with the most anomalies: **November** (3,428).
- High price spikes: **16,204**.
- Low price drops: **132**.

## Commodity Concentration

| Commodity | Anomalies | Anomaly rate |
|---|---:|---:|
| Potato | 9,646 | 2.95% |
| Onion | 3,213 | 1.08% |
| Wheat | 2,249 | 2.92% |
| Tomato | 813 | 3.06% |
| Rice | 415 | 5.33% |

## State Concentration

| State | Anomalies | Anomaly rate |
|---|---:|---:|
| Tamil Nadu | 9,085 | 13.65% |
| Kerala | 3,482 | 7.64% |
| Maharashtra | 1,110 | 2.14% |
| Karnataka | 739 | 5.14% |
| Madhya Pradesh | 375 | 0.67% |

## Most Anomaly-Prone Months

| Month | Anomalies | Anomaly rate |
|---|---:|---:|
| November | 3,428 | 5.64% |
| October | 2,213 | 3.28% |
| December | 2,032 | 3.93% |
| July | 1,900 | 2.50% |
| August | 1,873 | 2.73% |

Months are ordered by flagged-record count. The rate controls for the number of source records available in each month.

## Anomaly Types

- **High Price Spike:** the quote is over two commodity-level standard deviations above the mean. Possible explanations include local scarcity, quality premiums, weather disruption, or reporting errors.
- **Low Price Drop:** the quote is over two commodity-level standard deviations below the mean. Possible explanations include supply gluts, distress sales, low-grade produce, or reporting errors.

## Extreme Observations

- Highest spike: **Onion** at **Jehanabad, Bihar** on **2023-11-09** recorded INR 460,000, a z-score of **196.13**.
- Lowest drop: **Wheat** at **Shamshabad, Madhya Pradesh** on **2023-07-17** recorded INR 215, a z-score of **-7.63**.
