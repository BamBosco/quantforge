# Candidate 005 — Pre-Export Data-Selection Amendment 001

**Candidate ID:** `candidate_005`  
**Status:** **PENDING — observation only; no export authority.**

## Recorded non-row terminal observation

On 2026-08-24, the Dukascopy MT5 terminal displayed the account/server identity
`Dukascopy-demo-mt5-1`, `Demo Account — Hedge`, and `Dukascopy Bank SA` while
the `USDJPY` instrument was selected.

The native MT5 Bars export workflow reached a **Save As** dialog. Its
automatically displayed proposed CSV filename was:

`USDJPY_M1_201908010000_202308012300`

The dialog showed CSV / text-file output. This is evidence that the terminal
can prepare a USDJPY M1 native-export action for the displayed interval.

## What this observation does and does not establish

| Item | Status | Finding |
| --- | --- | --- |
| Dukascopy MT5 server/account identity | VERIFIED | Visible terminal title metadata as stated above. |
| USDJPY native M1 export workflow | VERIFIED | Save As dialog was reached with an M1-prefixed USDJPY filename. |
| Proposed terminal interval represented by displayed filename | OBSERVED | `2019-08-01 00:00` through `2023-08-01 23:00`; this differs from the proposed UTC evaluation end of `2023-08-01 23:59`. |
| File creation / download | NOT PERFORMED | Save was not clicked; no Candidate 005 CSV was created. |
| Market-row inspection | NOT PERFORMED | No bar/tick row was read, recorded, parsed, or analysed for this amendment. |
| GMT/UTC selection | UNKNOWN | The Save As dialog does not display the timestamp-basis selection. |
| BID/ASK side | UNKNOWN | The Save As dialog does not display the native side selection. |
| Latest USDJPY M1 archive boundary | UNKNOWN | A selected export end is not proof of the provider's current latest archive boundary. |
| Actual M1 coverage, continuity, schema, or session capacity | UNKNOWN | None can be inferred from a filename or a pre-save dialog. |

## Governance effect

This amendment does not replace the UTC/GMT-only requirement or the proposed
evaluation range in the base record. It also does not authorize export,
acquisition, confirmation creation, structural validation, strategy work,
replay, backtesting, optimization, tuning, simulation, or trading.

Before any future acquisition authorization, the precise intended end timestamp
must be fixed deliberately, the source timestamp basis must be visibly set to
GMT/UTC, and the native BID/ASK representation must be identified and pinned.
