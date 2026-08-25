# Candidate 003 — Data-Selection Record Amendment 003

## Identity and status

**Candidate ID:** `crabel_early_session_directional_breakout_candidate_003`

**Amends:** Candidate 003 frozen pre-inspection data-selection record and
Amendments 001–002.

**Amendment version:** `0.1.3-frozen-pre-inspection`

**Status:** Frozen confirmation export-boundary amendment. It changes neither
Candidate 003 v0.2 trading rules nor any validation or authorization gate.

## Observed MT5 confirmation export boundary

Before saving or opening a confirmation CSV, the Dukascopy MT5 **Bars → Export
Bars** dialog presented this filename:

`XAUUSD_M1_202308020104_202608202359.csv`

The confirmed MT5/Wine export clock is `Africa/Lagos` / WAT (`UTC+01:00`). The
frozen confirmation export-operation boundaries are therefore:

| Field | Frozen value |
| --- | --- |
| Venue/server | Dukascopy Bank SA / `Dukascopy-demo-mt5-1` |
| Symbol/timeframe | `XAUUSD` / M1 |
| Terminal-export clock start | `2023-08-02 01:04` WAT |
| Terminal-export clock end | `2026-08-20 23:59` WAT |
| UTC-normalized start | `2023-08-02T00:04:00+00:00` |
| UTC-normalized end | `2026-08-20T22:59:00+00:00` |
| Expected raw filename | `XAUUSD_M1_202308020104_202608202359.csv` |
| Role | Independent confirmation only |

## Relationship to evaluation and unchanged controls

The frozen evaluation coverage ends at `2023-08-01T22:54:00+00:00`. This
confirmation coverage begins at `2023-08-02T00:04:00+00:00`; it is later and
does not overlap. The observed terminal boundary limits do not alter the
required New York 08:20–13:30 session definition on included dates and do not
permit missing-bar inference or filling.

No confirmation row, price, signal, return, R value, or structural-quality
result was accessed to make this amendment. The confirmation export must be
saved directly to its role-separated directory, then checksum-manifested and
access-controlled from raw bytes only. It must remain unopened, unparsed,
unassessed, and unused until an authorized evaluation replay passes all frozen
gates.

Candidate 003 v0.2 remains frozen. The 0/+1/+3 point costs, >=709-session
minimum, >=100 completed-trade minimum, holdout, walk-forward, no-lookahead,
and all failure/promotion gates remain unchanged. This amendment authorizes no
replay, paper mode, MT5 execution, or live trading.
