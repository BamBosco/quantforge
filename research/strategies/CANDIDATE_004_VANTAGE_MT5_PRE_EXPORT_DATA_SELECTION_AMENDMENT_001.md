# Candidate 004 — Pre-Export Data-Selection Amendment 001

## Scope

**Candidate identifier:** `candidate_004` (data acquisition only)  
**Amends:** `CANDIDATE_004_VANTAGE_MT5_PRE_EXPORT_DATA_SELECTION.md`  
**Status:** **MANUAL EVALUATION EXPORT AUTHORIZED — amended terminal-selected boundary.**

This amendment is made before the evaluation file is saved. It changes no
strategy, rule, parameter, calendar conversion, source, timeframe, or analysis
permission.

## Evaluation acquisition boundary correction

The user-supplied MT5 Save As dialog identifies the selected native M1 export
boundary in its pending filename. Replace the evaluation request in the parent
record with the following exact terminal-formatted range and filename:

| Item | Amended value |
| --- | --- |
| Role | Evaluation |
| Symbol | Standard `XAUUSD` only |
| Timeframe | M1 |
| Requested terminal start | `2013.01.02 00:00` |
| Requested terminal end | `2023.12.29 23:56` |
| Required raw filename | `XAUUSD_M1_VantageMarkets_Demo_201301020000_202312292356.csv` |
| Required destination | `data/candidate_004_vantage_mt5_raw/evaluation/` |

The selected boundary is recorded exactly as terminal-formatted source metadata.
It is not labelled UTC or New York time; the historical server DST convention
remains `UNKNOWN`.

## Confirmation control

The confirmation selection remains unchanged and is not authorized for any row
inspection after it is exported. No confirmation file is created or accessed by
this amendment.

## Non-authorization

This amendment authorizes no review of bar values, structural assessment,
session counting, strategy creation, signals, returns, trades, replay,
backtest, optimization, tuning, paper/MT5/broker/live execution, or order
activity.
