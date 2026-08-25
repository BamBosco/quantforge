# Candidate 003 — Data-Selection Record Amendment 001

## Identity and status

**Candidate ID:** `crabel_early_session_directional_breakout_candidate_003`

**Amends:** `CRABEL_EARLY_SESSION_DIRECTIONAL_BREAKOUT_CANDIDATE_003_DATA_SELECTION_RECORD.md`, record version `0.1-frozen-pre-inspection`

**Amendment version:** `0.1.1-frozen-pre-inspection`

**Status:** Frozen, pre-inspection export-boundary amendment. It does not
modify Candidate 003 trading rules, create a new candidate, authorize replay,
or authorize paper or MT5 execution.

## Reason for amendment

During the MT5 **Bars → Export Bars** operation, before saving or opening any
raw file, the terminal presented an evaluation-export filename encoding these
available boundaries:

`XAUUSD_M1_201908010105_202308012354.csv`

This establishes that the MT5 export operation is offering data from
`2019-08-01 01:05` through `2023-08-01 23:54` on its export-clock basis, rather
than the nominal day-edge endpoints in the original selection record. This is
a terminal-availability fact only; no bar prices, signals, returns, performance,
or structural-quality results were accessed.

## Frozen replacement for the evaluation export operation

The original record's intended evaluation date interval remains 1 August 2019
through 1 August 2023. For the actual MT5 evaluation export, the frozen
operation boundaries are now:

| Field | Frozen value |
| --- | --- |
| Venue/server | Dukascopy Bank SA / `Dukascopy-demo-mt5-1` |
| Symbol/timeframe | `XAUUSD` / M1 |
| Terminal-export clock start | `2019-08-01 01:05` |
| Terminal-export clock end | `2023-08-01 23:54` |
| Expected export filename | `XAUUSD_M1_201908010105_202308012354.csv` |
| UTC normalization | Pending capture of the terminal-local export timezone at export time; it must not be inferred from this filename |
| Role | Evaluation only |

The five-minute day-edge limitations do not alter Candidate 003's required
08:20–13:30 `America/New_York` session definition. They do not permit filling,
assuming, or manufacturing any missing bar. The unchanged structural-quality
assessment must later determine whether at least 709 sessions are complete.

## What did not change

- Candidate 003 remains `0.1-draft-for-data-source-approval`.
- The 08:20–08:24 observation window, 08:25 entry, stop model, 13:30 exit,
  ambiguity rules, normalized-R calculation, non-sized convention, and 0/+1/+3
  point scenarios remain unchanged.
- The >=709 complete-session and >=100 completed-trade gates remain unchanged.
- Confirmation remains `2023-08-02` through `2026-08-20` in the original
  selection record and is not authorized for export now.
- The raw export must remain unopened and unparsed; its checksum manifest may
  be created later from raw bytes only after source-timezone and retrieval
  metadata are recorded.
- No replay, performance calculation, paper mode, EA/bridge, order API, or
  live trading is authorized.
