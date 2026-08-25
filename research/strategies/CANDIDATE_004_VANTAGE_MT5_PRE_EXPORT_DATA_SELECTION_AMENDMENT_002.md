# Candidate 004 — Pre-Export Data-Selection Amendment 002

## Scope

**Candidate identifier:** `candidate_004` (data acquisition only)  
**Amends:** pre-export record and Amendment 001  
**Status:** **MANUAL CONFIRMATION EXPORT AUTHORIZED — amended terminal-selected boundary.**

This amendment is made before the confirmation file is saved. It changes no
strategy, rule, parameter, calendar conversion, source, timeframe, or analysis
permission.

## Confirmation acquisition boundary correction

The user-supplied MT5 Save As dialog identifies the selected native M1 export
boundary in its pending filename. Replace the confirmation request in the
parent record with the following exact terminal-formatted range and filename:

| Item | Amended value |
| --- | --- |
| Role | Confirmation — sealed and uninspected after export |
| Symbol | Standard `XAUUSD` only |
| Timeframe | M1 |
| Requested terminal start | `2024.01.02 01:00` |
| Requested terminal end | `2026.08.21 23:56` |
| Required raw filename | `XAUUSD_M1_VantageMarkets_Demo_202401020100_202608212356.csv` |
| Required destination | `data/candidate_004_vantage_mt5_raw/confirmation/` |

The selected boundary is recorded exactly as terminal-formatted source metadata.
It is not labelled UTC or New York time; the historical server DST convention
remains `UNKNOWN`.

## Sealing requirement

After saving, this raw confirmation file may be moved unchanged, sized, hashed,
and manifest-recorded only. It must not be opened, previewed, parsed,
inspected, structurally assessed, analysed, or used for any strategy work.

## Non-authorization

This amendment authorizes no review of bar values, session counting, strategy
creation, signals, returns, trades, replay, backtest, optimization, tuning,
paper/MT5/broker/live execution, or order activity.
