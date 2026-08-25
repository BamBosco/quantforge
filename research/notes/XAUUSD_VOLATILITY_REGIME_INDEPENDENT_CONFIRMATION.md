# XAUUSD Volatility Regime — Independent Confirmation Protocol

## Status

**Prepared; awaiting an independent dataset.** This protocol follows the
initial pass recorded in
[`XAUUSD_INTRADAY_VOLATILITY_REGIME_2026-08-14.md`](../results/XAUUSD_INTRADAY_VOLATILITY_REGIME_2026-08-14.md).
It is not an authority to change the Risk Engine or trade.

## Required independent data

The confirmation data must meet every condition below:

- Be a new Headway Demo `XAUUSD` M1 export, or an independently sourced
  dataset whose provenance and price basis are documented.
- Start strictly after the end of the initial dataset:
  `2026-08-14T17:53:00+00:00`.
- Have its own immutable manifest, SHA-256 checksum, source timezone, and
  quality notes.
- Retain M1 OHLC and recorded spread values. Missing, duplicate, or
  spreadless required session windows remain exclusions.
- Contain at least 100 valid New York weekday observations after exclusions.

No rows may overlap the initial dataset. Combining overlapping data with the
initial replay would invalidate independence.

## Frozen confirmation procedure

1. Use the unchanged `xauusd_intraday_volatility_regime` configuration.
2. Build the same 08:20–08:50 predictor and 08:50–13:30 outcome proxies.
3. Fit the three-bucket median forecaster using the complete initial 756 valid
   observations only; do not refit it using confirmation outcomes.
4. Use the matching initial-dataset median as the confirmation baseline.
5. Score all valid confirmation sessions once with MAE.
6. Pass only if the model reduces MAE by at least 5% relative to the frozen
   baseline across at least 100 confirmation sessions.

## Decision rules

| Confirmation outcome | QuantForge decision |
| --- | --- |
| Meets every requirement | Consider a separate design for an advisory-only Risk Engine input. |
| Fails the MAE requirement | Freeze the volatility-regime hypothesis; do not tune it. |
| Insufficient or invalid data | Record the limitation and wait for a qualifying export. |

Even a pass does not authorize a risk action, paper trading, broker access, or
live trading. Any future Risk Engine advisory must be independently designed,
tested, and fail safely when its data is unavailable.
