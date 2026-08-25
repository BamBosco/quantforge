# ORB XAUUSD Headway Demo M1 — Three-Year Replay

## Status

**Research result only — not approved for paper or live trading.** The
unchanged baseline is too sensitive to small additional execution cost to pass
the capital-preservation gate.

## Reproducibility record

- Strategy profile:
  `config/strategies/orb_xauusd_headway_demo_baseline.toml`
- Dataset manifest:
  `config/datasets/headway_demo_xauusd_m1_20230814_20260814.toml`
- Dataset checksum verified before replay:
  `488fa6147f1814b6671e67f853ed59d796e227b87c9f7004626ccd30fde7ace7`
- Timestamp normalization: `America/Los_Angeles` at export time to UTC, then
  explicitly to `America/New_York` for strategy-session logic.
- Results unit: normalized R only. No quantity, account size, leverage, or
  dollar P&L assumption was made.

## Coverage

| Item | Count |
| --- | ---: |
| Weekday sessions identified | 781 |
| Incomplete 08:20–13:30 sessions excluded | 25 |
| Stretch warm-up sessions excluded | 10 |
| Sessions evaluated | 746 |
| Completed entries | 746 |
| Forced exits | 294 |
| Protective-stop exits | 452 |
| Ambiguous OCO bars | 0 |

## Cost sensitivity

Recorded bid/ask spread is used for every bar. Additional slippage is adverse
at entry and exit. It is a sensitivity range, not a claim about actual fills.

| Scenario | Additional slippage | Total R | Mean R per completed trade | Positive / negative trades |
| --- | ---: | ---: | ---: | ---: |
| Recorded spread only | 0 points | +1.3219 | +0.0018 | 257 / 489 |
| Plus 1 point | 1 point | -2.6958 | -0.0036 | 257 / 489 |
| Plus 3 points | 3 points | -10.6285 | -0.0142 | 257 / 489 |

## Interpretation

The recorded-spread-only outcome is effectively flat and is reversed by one
additional point of adverse slippage. This is **fragile**, not a tradable edge.
The baseline therefore fails the current promotion gate: no paper execution,
no live execution, and no post-hoc tuning of the ORB parameters.

This replay was exploratory because an in-sample/out-of-sample split had not
been predeclared before the longer export became available. The next valid
research step is to freeze this baseline, predeclare a chronological split, and
test any separate new hypothesis independently. A positive result in another
experiment would still require walk-forward and forward testing before any
promotion.
