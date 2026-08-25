# Research Validation Framework — Integration Check

## Purpose

This is a software integration check for the shared validation framework. It
does **not** create new evidence for ORB or convert the historical data into a
valid, previously unseen holdout period.

## Input

- Frozen two-sided ORB baseline configuration.
- Headway Demo XAUUSD three-year M1 dataset manifest:
  `headway_demo_xauusd_m1_20230814_20260814`.
- Checksum verified:
  `488fa6147f1814b6671e67f853ed59d796e227b87c9f7004626ccd30fde7ace7`.
- All three pre-existing cost scenarios: recorded spread, +1 point, and +3
  points adverse slippage.
- Standard validation protocol version 0.1.

## Framework output

| Control | Result |
| --- | ---: |
| Evaluated sessions per cost scenario | 746 |
| Development sessions | 596 |
| Final contiguous holdout sessions | 150 |
| Walk-forward windows per cost scenario | 5 |
| Research gate | Failed |

The gate correctly rejected the baseline because all three scenarios had
non-positive holdout total or mean R, and the +3-point scenario also had
non-positive development total and mean R.

## Boundary

The ORB baseline remains rejected for the reasons recorded in its existing
[three-year replay report](../results/ORB_XAUUSD_HEADWAY_DEMO_M1_THREE_YEAR_REPLAY_2026-08-14.md).
This check validates software behavior only. It does not authorise a further
ORB experiment, independent confirmation, paper trading, or live trading.
