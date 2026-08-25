# XAUUSD Intraday Volatility Regime — Proposed Research Hypothesis

## Status

**Initial research gate passed on 2026-08-14; independent confirmation only.**
See the [research result](../results/XAUUSD_INTRADAY_VOLATILITY_REGIME_2026-08-14.md).
No risk control, paper trading, or live trading is authorised.

This is intentionally not an entry strategy. It is a risk-research question
designed to improve future capital-preservation controls without pretending
that the current dataset provides a directional edge.

See the [source review](../papers/XAUUSD_INTRADAY_VOLATILITY_SOURCE_REVIEW.md).

## Plain-language question

Can the amount gold moves during the first 30 minutes of the chosen New York
research session help forecast whether gold will be unusually active for the
rest of that session?

If the answer is consistently yes, a future Risk Engine could use the result to
reduce or block new trade intents during unusually volatile conditions. A pass
would not create a buy or sell signal.

## Predeclared observation windows

| Item | Definition |
| --- | --- |
| Instrument | Headway Demo `XAUUSD` |
| Timezone | `America/New_York` |
| Eligible days | Weekdays with complete valid M1 and recorded spread data |
| Predictor window | 08:20:00 inclusive through 08:50:00 exclusive |
| Forecast window | 08:50:00 inclusive through 13:30:00 exclusive |
| Predictor | Sum of absolute one-minute bid close-to-close changes in the predictor window |
| Outcome | Sum of absolute one-minute bid close-to-close changes in the forecast window |

The use of absolute movement deliberately avoids treating up and down as a
directional prediction. M1 close-to-close movement is an available proxy only;
it is not realized volatility from ticks or trades.

## Fixed forecast and validation design

This research uses a separate forecasting-validation component rather than the
strategy R-multiple gate. The rules below are frozen before the first run.

### Observation formula

For each complete session, the predictor is the sum of absolute bid
close-to-close moves from 08:21 through 08:49. The outcome is the sum of
absolute bid close-to-close moves from 08:50 through 13:29. The 08:50 close
change is measured against the completed 08:49 close, so it belongs entirely
to the future forecast window. Both values are price-movement proxies, not
transaction-level realized volatility.

### Forecast rule

The forecast rule is deliberately simple and non-parametric:

1. Use only an earlier chronological training set of at least 252 valid
   sessions.
2. Sort the early-session predictor values in that training set and split them
   into low, middle, and high thirds using fixed nearest-rank cutoffs.
3. Assign the current session's predictor to one of those thirds.
4. Forecast its outcome as the median historical outcome within that same
   third. If a third contains fewer than 20 observations, use the overall
   historical median instead.

The baseline forecast is the overall median future-session movement from the
same training set. Both forecasts are created without seeing the target
session's future movement.

### Score and pass/fail gate

Forecast quality is measured by mean absolute error (MAE): the average absolute
difference between forecast movement and observed future movement. Lower is
better. The model's percentage improvement is
`1 - model_MAE / baseline_MAE`.

The candidate passes only when all of these are true:

1. At least 100 scored sessions exist in both development and holdout samples.
2. Across five fixed chronological development windows—252 training sessions,
   63 following validation sessions, stepped 63 sessions—the model improves
   MAE by at least 5% in at least four windows.
3. Across the concatenated development-window forecasts, model MAE improves by
   at least 5% over baseline MAE.
4. A model fitted only on the full development sample improves holdout MAE by
   at least 5% over its development-fitted baseline.

The final 20% of valid sessions remains the holdout. Missing, duplicate, or
spreadless M1 windows are excluded and counted. No threshold, time window,
proxy, or gate value may be changed after results are known.

## Risk and engineering boundaries

- This research component has no authority to approve, size, cancel, close, or
  place an order.
- Any future use must be an advisory input to the Risk Engine; the existing
  Risk Engine remains the only decision authority.
- No threshold, time window, or proxy may be changed after observing results.
- Tick volume must not be called exchange volume. VWAP, order flow, and depth
  remain unsupported by this dataset.
- News and scheduled events remain a separate future policy with their own
  audited calendar source.

## Why this is the next direction

ORB and the first directional intraday-momentum experiment both failed their
fixed research gates. Adding filters or inverting them would be data mining.
This separate hypothesis focuses on forecasting uncertainty—directly aligned
with capital preservation—before another directional strategy is considered.

## Result and implementation boundary

The fixed offline study passed its initial research gate. This permits only an
independent confirmation study using the same formula and gate; it does not
modify existing Risk Engine decisions, place trades, or authorise paper or live
trading. The complete result is retained in the
[research report](../results/XAUUSD_INTRADAY_VOLATILITY_REGIME_2026-08-14.md).

A separate future design would still be required before any advisory output
could be connected to the Risk Engine.
