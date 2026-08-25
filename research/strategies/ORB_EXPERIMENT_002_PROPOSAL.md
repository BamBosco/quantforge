# ORB Experiment 002 — Directional-Bias Proposal

## Status

**Replay completed and failed its research gate. Frozen. Parameter search,
paper trading, and live trading remain prohibited.**

This proposal is deliberately separate from the original ORB baseline. It is
not a repair of that baseline and must not overwrite its configuration or its
result.

## Why this experiment exists

The frozen two-sided baseline produced +1.3219 R using recorded spread only,
but -2.6958 R after one additional point of adverse slippage. That is too
fragile to be considered an edge. See the [three-year replay result](../results/ORB_XAUUSD_HEADWAY_DEMO_M1_THREE_YEAR_REPLAY_2026-08-14.md).

The Crabel review identifies a directional opening-range breakout (ORBP) as a
separate source-inspired idea: take only the breakout that agrees with a
pre-existing, objectively defined directional condition. This is a hypothesis,
not evidence that such a filter improves XAUUSD results.

## Single research question

For Headway Demo `XAUUSD`, does allowing only the opening-range breakout that
matches one predeclared directional-bias rule produce a less execution-fragile
outcome than the frozen two-sided baseline?

### Null hypothesis

The directional restriction does not improve the return distribution or its
robustness after realistic execution costs; any apparent improvement is noise.

## Scope that remains unchanged

To avoid data mining, the experiment changes **one thing only**: which side of
the existing OCO entry is eligible. Unless explicitly amended in a later,
approved proposal, all of the following remain exactly as in the frozen
baseline:

| Control | Fixed definition |
| --- | --- |
| Venue and symbol | Headway Demo `XAUUSD` |
| Strategy session | 08:20–13:30 `America/New_York` |
| Opening range | 08:20–08:35 New York time (15 minutes) |
| Entry buffer | Ten-session Crabel Stretch |
| Entry model | Stop entry at the eligible range boundary; no opposing entry once a side is selected |
| Protective stop | Opposite range side plus the same buffer |
| Trade limit | One completed entry per session |
| Exit | 13:30 New York market exit if the protective stop has not exited |
| Data handling | Exclude incomplete, invalid, ambiguous, and warm-up sessions exactly as before |
| Cost model | Recorded bar spread plus predeclared adverse-slippage scenarios of 0, +1, and +3 points |
| Risk result | Normalized R only; no sizing, account value, leverage, or broker order submission |

## Selected directional-bias rule

**Selection made on 2026-08-14: overnight directional bias.** This is the
simplest rule that tests the directional ORBP idea without introducing a
threshold, indicator, or additional parameter to optimise.

For each New York trading date:

1. Take the open of the M1 bar at `00:00:00 America/New_York`.
2. Take the close of the completed M1 bar at `08:19:00 America/New_York`.
3. If the 08:19 close is greater than the 00:00 open, the bias is `long` and
   only the existing buy-stop entry is eligible.
4. If the 08:19 close is less than the 00:00 open, the bias is `short` and
   only the existing sell-stop entry is eligible.
5. If the prices are equal, either bar is unavailable or invalid, the bias is
   `neutral` and the session is a **no trade** with a recorded reason.

No value from 08:20 onward can influence the bias. The strategy therefore
knows its eligible side before the opening range begins and cannot use future
price information. The opening range itself, the entry buffer, stop, trade
limit, cost model, and exit remain unchanged.

This rule is a deliberately simple first hypothesis, not a claim that the
overnight move predicts the New York opening-range breakout.

## Proposed controls and acceptance gate

- Test exactly one approved bias formula, with no parameter sweep and no
  simultaneous VWAP, volume, news, gap, or volatility filter.
- Preserve the raw data, manifest checksum, timestamp normalization, and full
  event log for reproducibility.
- Report every eligible session, every excluded session and reason, every
  rejected signal, and every completed simulated trade.
- Compare the new result with the frozen two-sided baseline using the same
  dataset and cost scenarios. Do not compare only the best subset of dates.
- Treat the existing three-year dataset as exploratory because it has already
  been viewed during the baseline study.
- The historical experiment passes its *research gate* only if it has at least
  100 completed simulations and has both total R greater than zero and mean R
  per completed trade greater than zero in **each** of the recorded-spread, +1
  point, and +3 point adverse-slippage scenarios. This permits only
  independent confirmation work; it does not permit paper or live trading.
- Keep a future, untouched forward-confirmation period after the experiment is
  specified. A favorable historical result is not permission for paper trading.

## Explicitly out of scope

- Changing the opening time, range duration, Stretch lookback, stop placement,
  exit time, or slippage scenarios to make results look better.
- Adding multiple filters together.
- Optimising a threshold until it succeeds.
- Position sizing, dollar P&L, portfolio construction, broker connectivity,
  MT5 automation, paper trading, or live trading.

Scheduled-event protection is governed separately by the platform
[News and Event Risk Policy](../../docs/NEWS_EVENT_RISK_POLICY.md). It must be
researched as its own change; applying it here would combine two unvalidated
changes.

## Result

The fixed replay was run exactly once and failed: it was negative in every
cost scenario, including recorded-spread only. See the full
[result report](../results/ORB_XAUUSD_HEADWAY_DEMO_OVERNIGHT_BIAS_REPLAY_2026-08-14.md).
No follow-up tuning or promotion is permitted. The frozen two-sided baseline
also remains unchanged.
