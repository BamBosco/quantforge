# Candidate 004 — Vantage MT5 Pre-Export and Data-Selection Record

## Status and scope

**Candidate identifier:** `candidate_004`  
**Stage:** data acquisition only; no strategy exists or is authorized.  
**Status:** **MANUAL ACQUISITION AUTHORIZED — two raw, role-separated exports only.**

This record is evidence-first. It authorizes the manual acquisition and freezing
of the two raw MT5 files defined below; it does not authorize changing their
contents, structural-quality assessment, market-behaviour inspection, signal or
performance calculation, replay, backtest, optimization, tuning, paper trading,
MT5 execution, broker execution, or live trading.

## Source identity and timestamp evidence

| Item | Value | Status |
| --- | --- | --- |
| Broker/entity | Vantage Markets (Pty) Ltd | Verified |
| MT5 server | `VantageMarkets-Demo` | Verified |
| Account environment | Demo Account — Hedge | Verified |
| Instrument | Standard `XAUUSD` — Gold US Dollar | Verified; `XAUUSD247` excluded |
| Native source | MT5 Symbols → Bars → `Export Bars` | Verified |
| Timeframe | M1 | Verified |
| Live XAUUSD observation | 24 Aug 2026: terminal chart approximately two hours ahead of the `Africa/Lagos` workstation clock | Verified observation |
| Observed server offset at that moment | UTC+3 | Verified only for the observed August 2026 moment |
| Historical server DST convention | `UNKNOWN` | Unresolved; no UTC+2/UTC+3 historical assumption permitted |

The requested timestamps below are raw **terminal-formatted MT5 timestamps**.
They are not labelled UTC or New York time. Candidate 003 assumptions are not
used anywhere in this record.

## Frozen requested acquisition ranges

The displayed native M1 interface previously evidenced an apparent terminal
span beginning no later than `2012.08.02 01:00` and extending at least to
`2026.08.21 00:00`. On that evidence, the following raw, non-overlapping
terminal-date ranges are selected for acquisition. They do not constitute
research-calendar dates or a strategy evaluation design.

| Role | Requested terminal timestamp range | Required raw filename | Required destination |
| --- | --- | --- | --- |
| Evaluation | `2013.01.01 00:00` through `2023.12.31 23:59` | `XAUUSD_M1_VantageMarkets_Demo_201301010000_202312312359.csv` | `data/candidate_004_vantage_mt5_raw/evaluation/` |
| Confirmation | `2024.01.01 00:00` through `2026.08.21 23:59` | `XAUUSD_M1_VantageMarkets_Demo_202401010000_202608212359.csv` | `data/candidate_004_vantage_mt5_raw/confirmation/` |

The confirmation export must be retained as a sealed later/non-overlapping raw
file. Its rows must not be opened, previewed, parsed, inspected, analysed, or
used after acquisition.

## Required manifest fields

Create one sidecar manifest for each file only after its SHA-256 is calculated:

```toml
dataset_role = "evaluation_or_confirmation"
filename = "exact_raw_filename.csv"
source = "Vantage MT5 native Bars export"
broker_entity = "Vantage Markets (Pty) Ltd"
server = "VantageMarkets-Demo"
symbol = "XAUUSD"
timeframe = "M1"
retrieved_at_local = "YYYY-MM-DDTHH:MM:SS±HH:MM"
requested_terminal_start = "YYYY.MM.DD HH:MM"
requested_terminal_end = "YYYY.MM.DD HH:MM"
sha256 = "lowercase_64_character_hex_digest"
historical_server_dst_convention = "UNKNOWN"
observed_server_offset_evidence = "UTC+3 observed on 2026-08-24 only"
raw_file_preserved_unmodified = true
confirmation_uninspected = true
```

`actual_reported_coverage` may be added only if MT5 reports it as interface
metadata. It must not be derived by opening, parsing, or examining rows.

## Completion condition

After both files have been manually exported, moved without modification,
checksummed, and manifest-recorded, stop. Report only filename, byte size,
SHA-256, requested range, any metadata-only reported coverage, server name,
observed timezone evidence, and remaining historical timezone/DST unknowns.
No structural-quality assessment is authorized at that point.
