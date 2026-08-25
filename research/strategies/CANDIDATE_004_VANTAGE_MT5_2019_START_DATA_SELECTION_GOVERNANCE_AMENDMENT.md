# Candidate 004 — 2019-Start Data-Selection Governance Amendment

## Status and effect

**Candidate identifier:** `candidate_004` (data-source governance only)
**Status:** **FUTURE-ACQUISITION SELECTION ONLY — no export authorization.**
**Supersedes:** only the future-acquisition selection of the 2013-based
Candidate 004 evaluation horizon in
`CANDIDATE_004_VANTAGE_MT5_PRE_EXPORT_DATA_SELECTION.md` and Amendment 001.

This is a data-selection correction. It does not create a Candidate 004
strategy, change any trading rule, alter the standard validation protocol,
change a minimum-session/trade gate, authorize replay, or authorize performance
analysis.

## Basis for correction

The standard chronological validation protocol specifies a holdout fraction,
walk-forward session lengths, and research gates; it contains no mandatory
calendar start date. The >=709 complete-session requirement is a capacity gate,
not a requirement to obtain data beginning in 2013.

The 2013 start was introduced solely by the earlier Candidate 004 pre-export
record after an apparent terminal availability observation. It was not inherited
from Candidate 001, 002, or 003 and was not required by the research protocol.

For a date-only acquisition precedent, this amendment adopts Candidate 003's
predeclared four-year evaluation span, 1 August 2019 through 1 August 2023.
Candidate 003's broker, data, UTC normalization, timezone evidence, strategy,
and performance are not inputs to Candidate 004.

## New future evaluation acquisition selection

| Field | Selected value |
| --- | --- |
| Role | Future Candidate 004 evaluation acquisition only |
| Venue/symbol | Vantage `VantageMarkets-Demo`, standard `XAUUSD` only |
| Timeframe | M1 |
| Requested raw terminal start | `2019.08.01 00:00` |
| Requested raw terminal end | `2023.08.01 23:59` |
| Date-selection rationale | Candidate 003's established 2019.08.01–2023.08.01 four-year precedent; chronology; potential capacity above the unchanged >=709 gate |
| Timestamp status | Terminal-formatted source timestamps only; no UTC, UTC+2, UTC+3, Lagos, or New York label is assigned |

The selected start/end are acquisition controls, not a claim that all timestamps
within them are complete, M1-valid, timezone-convertible, or eligible for any
future strategy session.

## Confirmation preservation and chronology

The existing confirmation raw CSV and manifest remain exactly as frozen in
`data/candidate_004_vantage_mt5_raw/confirmation/`. They remain later than the
new proposed evaluation horizon and completely uninspected. This amendment does
not open, rename, checksum, parse, preview, move, reassign, or otherwise access
them.

## Existing evaluation artifact preservation

The existing frozen 2013–2023 Vantage evaluation CSV and manifest remain
immutable audit artifacts. They must not be deleted, modified, subsetted,
relabeled, merged, or used as the new 2019-start evaluation dataset. The
structural FAIL applies to that 2013-based artifact and does not by itself
establish failure of a separately acquired 2019-start file.

## Mandatory blockers before any new evaluation freeze

1. Establish an evidence-supported historical Vantage server timezone/DST
   convention for the 2019–2023 source timestamps and a valid conversion to
   `America/New_York`.
2. Establish whether the exported spread field is sufficiently complete and
   semantically adequate for the eventual execution-price model, including
   whether bid/ask-side requirements can be supported.
3. Establish complete M1-session capacity for the selected 2019–2023 horizon
   after the future strategy-required session is separately frozen; calendar
   weekdays cannot substitute for complete sessions.
4. Establish a new raw file's homogeneous M1 coverage, timestamp continuity,
   duplicates, malformed rows, OHLC validity, and Vantage-specific
   holiday/maintenance/early-close limitations in a separately authorized
   structural assessment.
5. Create a future, specific export authorization and a new raw evaluation
   file/manifest only after the preceding source-governance evidence is
   sufficient. No such authorization is created by this amendment.

## Non-authorization

No existing Candidate 004 file is changed. No confirmation access, data export,
structural assessment, strategy definition, signal generation, return/trade
calculation, replay, backtest, optimization, tuning, paper execution, MT5
execution, broker execution, or live execution is authorized.
