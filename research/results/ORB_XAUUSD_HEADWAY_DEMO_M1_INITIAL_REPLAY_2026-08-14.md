# ORB XAUUSD Headway Demo M1 — Initial Replay

## Status

**Withdrawn — do not interpret this result.** The replay used an incorrect
source-timezone assumption before MT5 Bars export timestamps were verified.
It is retained only as an audit record and does not establish an edge or
authorize paper or live execution.

## Reproducibility record

- Strategy profile:
  `config/strategies/orb_xauusd_headway_demo_baseline.toml`
- Dataset manifest:
  `config/datasets/headway_demo_xauusd_m1_20260505_20260814.toml`
- Dataset checksum verified before replay:
  `51a8bf300863451412445f367022a96c2fb34f51633f92c2bfd788b301ec5741`
- Instrument: Headway Demo `XAUUSD`
- Data: 99,872 M1 bars, 2026-05-05 through 2026-08-14
- Strategy session: 08:20–13:30 `America/New_York`
- Results unit: normalized R only; no quantity, account balance, leverage, or
  dollar P&L assumption was made.

The former broker-timezone assumption was incorrect. A replacement replay will
use the Mac timezone recorded in the dataset manifest at export time.

## Data eligibility

| Item | Count |
| --- | ---: |
| Weekday dates in the export | 74 |
| Dataset-quality exclusions | 10 |
| Stretch warm-up sessions | 10 |
| Evaluated sessions | 54 |
| Completed entries | 54 |
| Ambiguous same-bar OCO events | 0 |
| Forced exits | 15 |
| Protective-stop exits | 39 |

The 10 quality exclusions are recorded in the dataset manifest and include
partial exports, special/short sessions, and sessions with observed M1 gaps.
They were not used in results or in the ten-session Stretch history.

## Cost sensitivity results

Recorded bid/ask spread is used in every case. “Additional slippage” is applied
adversely to entries and exits. These are sensitivity cases, not estimates of
actual Headway fills.

| Scenario | Additional slippage | Total R | Mean R per completed trade | Positive / negative trades |
| --- | ---: | ---: | ---: | ---: |
| Recorded spread only | 0 points | -12.3947 | -0.2295 | 14 / 40 |
| Plus 1 point | 1 point | -12.5127 | -0.2317 | 14 / 40 |
| Plus 3 points | 3 points | -12.7476 | -0.2361 | 14 / 40 |

## Interpretation

This small May-to-August sample is negative under every declared cost scenario.
That is an early **do-not-promote** signal for this exact baseline on this exact
dataset; it is not a conclusion about ORB generally, gold generally, or a
different venue/time period. The sample is too short and lacks tick sequencing,
out-of-sample separation, walk-forward testing, and forward testing.

No parameter should be changed in response to this result yet. The next valid
research step is to acquire a longer, checksum-recorded M1 or tick dataset and
predeclare an in-sample/out-of-sample split before comparing the unchanged
baseline with any separate hypothesis.
