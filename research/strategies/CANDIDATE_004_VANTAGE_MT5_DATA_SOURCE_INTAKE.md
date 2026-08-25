# Candidate 004 — Vantage MT5 XAUUSD Data-Source Intake

## Scope and status

**Candidate identifier:** `candidate_004` (data-source intake only)  
**Venue under assessment:** Vantage MT5  
**Requested instrument:** standard `XAUUSD` only; `XAUUSD247` is excluded.  
**Status:** **PENDING — not approved for export, structural inspection, replay, or strategy work.**

This is not a Candidate 004 trading strategy or specification. It creates no
trading hypothesis, rules, cost model, evaluation result, confirmation dataset,
paper mode, MT5 bridge, broker connection, or execution authority. No market
data row, CSV, chart, export, confirmation dataset, or strategy performance was
opened, parsed, previewed, exported, or analyzed for this record.

## Local environment observation

`/Applications/MetaTrader 5.app` and its local MetaQuotes/Wine support folder
are present. The MT5 user interface did not become readable through the
available read-only inspection channel. A generic MT5 installation does not
establish Vantage broker identity, account state, server, symbol availability,
or historical-data capability; all such facts remain `UNKNOWN`.

## Vantage MT5 instrument and source facts

| Fact | Verified value | Status / evidence |
| --- | --- | --- |
| Broker/entity name | `UNKNOWN` | MT5 account UI unavailable; do not infer from an installation. |
| MT5 server name | `UNKNOWN` | Not observed. |
| Account/demo status | `UNKNOWN` | Not observed. |
| Requested symbol | standard `XAUUSD` only | User scope; availability not verified. |
| Exact broker symbol | `UNKNOWN` | Must be read from Vantage MT5 Symbols/Specification. |
| `XAUUSD247` | Excluded | Must not be selected. |
| Description | `UNKNOWN` | Not observed. |
| Digits | `UNKNOWN` | Not observed. |
| Point size | `UNKNOWN` | Not observed. |
| Tick size | `UNKNOWN` | Not observed. |
| Tick value | `UNKNOWN` | Not observed. |
| Contract size | `UNKNOWN` | Not observed. |
| Minimum volume | `UNKNOWN` | Not observed. |
| Volume step | `UNKNOWN` | Not observed. |
| Maximum volume | `UNKNOWN` | Not observed. |
| Volume limit | `UNKNOWN` | Not observed. |
| Spread type | `UNKNOWN` | Not observed. |
| Execution type | `UNKNOWN` | Not observed. |
| Trading sessions | `UNKNOWN` | Not observed. |
| Bid/ask availability | `UNKNOWN` | Must be evidenced by symbol specification and prospective export schema. |
| M1 availability | `UNKNOWN` | Not observed. |
| Historical M1 boundary/depth | `UNKNOWN` | Must be read from the MT5 Bars export-dialog boundary only, before export. |
| MT5 server/source timezone | `UNKNOWN` | Must be established and recorded at export; never inferred from the Mac clock. |
| Exported timestamp basis | `UNKNOWN` | Must be established before later structural inspection. |

## Minimum governance records before future data inspection

1. This source-intake/feasibility record, updated only with observed terminal
   facts and a PASS/PENDING/FAIL source decision.
2. A frozen pre-inspection data-selection record after terminal M1 boundaries
   are observed. It must predeclare an older evaluation range and a later,
   non-overlapping confirmation range solely from availability and protocol
   facts, not market behavior.
3. Separate evaluation and confirmation raw exports, each placed in its own
   role directory, with a SHA-256 manifest, terminal/server/account provenance,
   timezone, selected boundaries, retrieval time, and owner-read-only freeze.
   Neither raw export may be inspected before its role and checksum are frozen.
4. A separately authorized structural-quality assessment of the evaluation raw
   export only. It may test schema, continuity, timestamps, fields, and session
   completeness, but not strategy performance.
5. A separately approved Candidate 004 strategy specification and later replay
   authorization, if and only if all preceding gates are satisfied. No
   confirmation inspection/replay is implied by an evaluation pass.

## Date-range status

No evaluation or confirmation dates are predeclared because Vantage's earliest
and latest retrievable M1 boundaries are `UNKNOWN`. Once observed in the native
MT5 export dialog, select only by those boundaries and chronological separation:

- evaluation: an older contiguous interval with calendar capacity to potentially
  meet the protocol's >=709 complete-session gate;
- confirmation: a later contiguous interval, strictly non-overlapping with
  evaluation, likewise with potential capacity;
- no price, signal, return, trade, or performance information may influence the
  split.

## Decision

**PENDING.** Vantage has not passed identity, standard-symbol, instrument
specification, M1-depth, timestamp-provenance, export-schema, or role-separation
feasibility gates. This status grants no export, row-level inspection, replay,
optimization, tuning, paper/live execution, or confirmation access.
