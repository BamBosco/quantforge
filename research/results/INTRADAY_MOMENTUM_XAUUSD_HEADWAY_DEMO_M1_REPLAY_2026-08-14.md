# Intraday Momentum XAUUSD Headway Demo M1 — Experiment 001 Replay

## Decision

**Rejected and frozen.** This fixed, price-only momentum hypothesis fails the
predeclared QuantForge research gate at every tested cost scenario. It is not
approved for confirmation, paper trading, live trading, or parameter tuning.

The later holdout period was positive, but the earlier development period and
four of five walk-forward validation periods were not. Treating only the
positive holdout as evidence would be selection bias.

## Reproducibility record

- Strategy specification:
  [`INTRADAY_MOMENTUM.md`](../strategies/INTRADAY_MOMENTUM.md)
- Strategy profile:
  `config/strategies/intraday_momentum_xauusd_headway_demo.toml`
- Dataset manifest:
  `config/datasets/headway_demo_xauusd_m1_20230814_20260814.toml`
- Dataset SHA-256 verified before replay:
  `488fa6147f1814b6671e67f853ed59d796e227b87c9f7004626ccd30fde7ace7`
- Timestamp treatment: `America/Los_Angeles` at export time, normalized to
  UTC, then converted explicitly to `America/New_York` for session logic.
- Validation protocol:
  `config/research/standard_validation_protocol.toml` version `0.1`
- Result unit: normalized R only. No quantity, capital, leverage, or dollar
  P&L assumption was made.

## Fixed experiment

For each complete New York weekday, observe bid price from 08:20 through the
completed 08:49 M1 bar. If it rose, submit a buy market intent at 08:50; if it
fell, submit a sell market intent. A buy stop is the lowest bid low in that
signal window; a sell stop is the highest recorded ask high. Any surviving
position exits at the 13:30 M1 open. Recorded spread is used at every relevant
bar and adverse fixed slippage is applied at entry and exit.

No volume, VWAP, order-flow, order-book, news, target, re-entry, or filter was
used. An entry M1 bar that also touched the protective stop was marked
ambiguous and excluded from trade performance rather than assigned an invented
fill order.

## Coverage and outcome journal

| Outcome | Sessions |
| --- | ---: |
| New York weekdays identified | 781 |
| Forced exits | 246 |
| Protective-stop exits | 501 |
| Completed trades | 747 |
| Ambiguous entry/stop M1 bars | 8 |
| Neutral signals; no trade | 1 |
| Incomplete, duplicate, or spreadless required windows | 25 |
| Risk rejections | 0 |

All three cost scenarios evaluated the identical 781 session dates and had
the same terminal-outcome counts. The ambiguous sessions were 2024-01-02,
2024-02-16, 2024-06-14, 2024-08-14, 2025-02-27, 2026-02-06, 2026-05-11, and
2026-06-19. The neutral session was 2024-07-30. The 25 invalid-data windows
remain excluded from performance rather than repaired or inferred.

## Full-sample cost sensitivity

| Scenario | Completed trades | Wins / losses | Total R | Mean R | Max drawdown (R) | Profit factor |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Recorded spread only | 747 | 216 / 531 | -23.0351 | -0.0308 | 55.1209 | 0.9550 |
| Plus 1 point | 747 | 214 / 531 | -28.3251 | -0.0379 | 57.3988 | 0.9449 |
| Plus 3 points | 747 | 212 / 535 | -38.7141 | -0.0518 | 65.3689 | 0.9253 |

The rule loses even under recorded-spread-only assumptions. Higher adverse
slippage worsens the result, as expected.

## Chronological validation

The final 20% of calendar sessions was held out before applying the common
research gate: 624 development sessions and 157 holdout sessions. The
performance values below include only completed trades; the session sequence
also preserves no-trade, ambiguous, and invalid-data records.

| Scenario | Development total / mean R | Holdout total / mean R | Positive walk-forward validations |
| --- | ---: | ---: | ---: |
| Recorded spread only | -38.2405 / -0.0639 | +15.2053 / +0.1020 | 1 / 5 |
| Plus 1 point | -43.1337 / -0.0721 | +14.8086 / +0.0994 | 1 / 5 |
| Plus 3 points | -52.7342 / -0.0882 | +14.0200 / +0.0941 | 1 / 5 |

The protocol requires positive development total and mean R in every cost
scenario and at least two positive walk-forward validation windows. Those
requirements fail in every scenario. The positive holdout is retained as an
observation, not used to override the failed development evidence.

## Final gate result

**Failed.** The experiment has sufficient trade count but fails positive
development total R, positive development mean R, and the minimum number of
positive walk-forward validations under all three cost scenarios.

The specification is now frozen. Any later intraday-momentum idea must be a
new, separately documented hypothesis with its own rationale and approval; it
must not be presented as a repair of this experiment.
