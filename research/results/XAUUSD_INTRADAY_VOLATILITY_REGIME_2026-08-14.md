# XAUUSD Intraday Volatility Regime — Initial Research Result

## Decision

**Passed the initial research gate for independent confirmation only.** The
predeclared non-trading forecast reduced error against its simple historical
median baseline in all five development windows and in the untouched holdout.

This result does **not** authorise a new strategy, a risk limit, paper trading,
live trading, or any connection to MT5. It establishes only that this exact
offline volatility proxy warrants an independent confirmation study.

## Reproducibility record

- Hypothesis:
  [`XAUUSD_INTRADAY_VOLATILITY_REGIME.md`](../strategies/XAUUSD_INTRADAY_VOLATILITY_REGIME.md)
- Study configuration:
  `config/research/xauusd_intraday_volatility_regime.toml` version `0.1`
- Dataset manifest:
  `config/datasets/headway_demo_xauusd_m1_20230814_20260814.toml`
- Dataset SHA-256 verified before run:
  `488fa6147f1814b6671e67f853ed59d796e227b87c9f7004626ccd30fde7ace7`
- Timestamp treatment: `America/Los_Angeles` at export time, normalized to
  UTC and then converted to `America/New_York` for the study calendar.
- No order, fill, position, account, capital, leverage, or P&L calculation
  exists in this study.

## Method frozen before the run

The predictor is total absolute bid close-to-close price movement from 08:21
through 08:49 New York time. The target is total absolute bid close-to-close
movement from 08:50 through 13:29, with the first target change measured from
the 08:49 close. This is an M1 price-movement proxy, not transaction-level
realized volatility.

For each evaluation period, the model fits only its prior training sessions.
It divides early-session movement into historical low, middle, and high thirds
and forecasts later movement using the median prior outcome in the matching
third. The benchmark predicts the overall training median later movement.
Accuracy is evaluated by mean absolute error (MAE), where lower is better.

## Data coverage

| Item | Count |
| --- | ---: |
| New York weekdays identified | 781 |
| Valid complete observations | 756 |
| Excluded incomplete, duplicate, or spreadless M1 windows | 25 |
| Development observations | 604 |
| Untouched holdout observations | 152 |
| Development walk-forward windows | 5 |
| Scored development forecasts | 315 |
| Scored holdout forecasts | 152 |

## Forecast accuracy

The reported units are the dataset's raw XAUUSD price-movement units. They are
not dollars of profit or loss.

| Evaluation period | Baseline MAE | Model MAE | Error reduction |
| --- | ---: | ---: | ---: |
| Development windows combined | 63.0975 | 45.9606 | 27.16% |
| Untouched holdout | 265.1573 | 174.9080 | 34.04% |

| Development window | Baseline MAE | Model MAE | Error reduction |
| --- | ---: | ---: | ---: |
| 1 | 28.9083 | 16.4098 | 43.24% |
| 2 | 25.3240 | 20.3718 | 19.56% |
| 3 | 93.0504 | 83.1133 | 10.68% |
| 4 | 56.7529 | 34.4266 | 39.34% |
| 5 | 111.4517 | 75.4817 | 32.27% |

## Gate assessment

The frozen gate required at least 100 scored development and holdout sessions,
at least 5% MAE improvement in combined development and holdout tests, and at
least four of five development windows meeting the 5% threshold.

All requirements passed:

- 315 development and 152 holdout forecasts exceeded the minimum sample size.
- Development error reduction was 27.16%, above 5%.
- Holdout error reduction was 34.04%, above 5%.
- Five of five development windows exceeded 5%.

## Important limits and next action

The data comes from one Headway demo XAUUSD export and measures only price
movement. It does not establish prediction of direction, execution quality,
expected profit, exchange liquidity, or resilience in another broker, time
period, or market regime.

The next permitted action is an **independent confirmation study** using a
separate later export or a genuinely independent data source, under the same
frozen formula and gate. A separate architecture and safety review would still
be necessary before this information could become a Risk Engine advisory input.
The exact independent-data and confirmation rules are retained in the
[independent confirmation protocol](../notes/XAUUSD_VOLATILITY_REGIME_INDEPENDENT_CONFIRMATION.md).
