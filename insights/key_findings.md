# Interview-Ready Business Findings

These findings describe the supplied dataset after cleaning 736,711 market
quotes from 6 June 2023 through 11 June 2025. They identify investigation
priorities, not causal proof.

## 1. Onion Shows the Highest Relative Volatility

Onion has the highest coefficient of variation at **83.81%**, narrowly above
Tomato at 81.36% and Potato at 79.14%. Onion's mean modal price is INR 2,781.61
with a standard deviation of INR 2,331.19. Its Kharif average is INR 3,208.21,
79.8% above its Zaid average of INR 1,784.09. This combination suggests that
seasonal supply timing and extreme local quotes materially affect price
stability. Arrival quantities, storage stocks, weather, and grade should be
added before assigning a cause.

## 2. The Lowest-Cost State Depends on the Commodity

Among states with at least 30 observations, Madhya Pradesh is cheapest for
Onion at **INR 1,566.89** and Tomato at **INR 2,927.00**. Punjab is cheapest
for Potato at INR 1,119.09, Rajasthan for Rice at INR 3,126.73, and
Chhattisgarh for Wheat at INR 2,200.21. There is no single universally cheap
state; sourcing decisions should therefore be crop-specific and should include
transport cost, quality, and sample size.

## 3. Seasonal Effects Are Strongest for Perishables

Tomato's Kharif average of **INR 5,794.07** is 193.7% above its Rabi average of
INR 1,972.68. Onion and Potato also peak in Kharif, while Wheat peaks in Rabi
at INR 2,541.57. Rice appears only in Zaid in this dataset, so a cross-season
Rice conclusion would be unsupported. The pattern is consistent with seasonal
supply pressure, but the dataset alone cannot distinguish weather, arrivals,
storage, or reporting mix.

## 4. Extreme Market Dispersion Is a Supply-Chain and Data-Quality Signal

Patna (Musallahpur), Bihar has the highest average among markets with at least
30 records at **INR 44,409.68**, while the overall dataset average is INR
2,474.96. This gap is too large to treat as a normal logistics premium without
record-level review. It points analysts toward unit consistency, commodity
mix, grade, local scarcity, and market connectivity as the first checks.

## 5. Anomaly Clusters Are Red Flags, Not Proof of Manipulation

The two-standard-deviation rule flags **16,336 records (2.22%)**: 16,204 high
spikes and 132 low drops. Potato contributes 9,646 flags, and Tamil Nadu has
9,085. November has the highest monthly count at 3,428. In addition, 1,246
records have a modal price outside their stated minimum-to-maximum range.
Repeated same-day divergence from nearby markets, unusual quote clustering,
and inconsistent ranges warrant audit, but manipulation should not be alleged
without arrivals, trader, auction, grade, and enforcement data.
