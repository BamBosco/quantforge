# Crabel Early-Session Directional Breakout — Candidate 002 v0.2

## Formal research-data-governance amendment

**Candidate ID:** `crabel_early_session_directional_breakout_candidate_002`  
**Supersedes:** Candidate 002 `0.1-frozen` for research-data-governance planning only  
**Version:** `0.2-frozen`  
**Status:** Frozen governance amendment. Data selection is pending. This document
does not authorize raw-data inspection, structural quality assessment, replay,
paper trading, MT5 execution, or live trading.

## Purpose and decision record

Candidate 002 v0.1 selected a frozen Exness evaluation export with 522 complete
08:20–13:30 New York sessions. The frozen protocol requires at least 709 valid
sessions after exclusions. The v0.1 export is therefore inadequate for the
predeclared validation structure.

Candidate 002 v0.1 also prohibited replacement of its selected raw exports.
Consequently, that export cannot be silently supplemented, merged, relabelled,
or replaced under v0.1.

No Candidate 002 replay has been run. No Candidate 002 strategy-performance
result has been calculated or inspected. This is a data-selection sufficiency
finding only; it is not a failure of the trading hypothesis.

This v0.2 document is a transparent, versioned amendment to the research-data
governance plan. It preserves Candidate 002's identity and all trading,
cost, validation, no-lookahead, contamination, and promotion rules. It does
not create a new strategy candidate.

## Immutable provisions carried forward from v0.1

Except for the replacement data-governance plan below, every provision of
Candidate 002 v0.1 remains exactly in force, including:

| Provision | v0.2 status |
| --- | --- |
| Candidate ID, Exness-MT5Trial9 venue, and `XAUUSDm` instrument | Unchanged |
| Crabel early-session directional hypothesis | Unchanged |
| `America/New_York` session and DST treatment | Unchanged |
| 08:20–08:24 completed-M1 observation window | Unchanged |
| 08:25 entry rule, sides, and one-entry-per-date limit | Unchanged |
| Stop definitions, validity rule, and fill model | Unchanged |
| 13:30 forced exit and its terminal precedence | Unchanged |
| 08:25 ambiguity exclusion | Unchanged |
| Recorded spread and 0/+1/+3-point adverse-slippage scenarios | Unchanged |
| Exact normalized-R formula and decimal treatment | Unchanged |
| Non-sized research convention | Unchanged |
| At least 100 completed trades in every cost scenario | Unchanged |
| At least 709 valid sessions after exclusions | Unchanged |
| Chronological validation, 20% untouched holdout, and walk-forward structure | Unchanged |
| Pass/failure gates | Unchanged |
| No-lookahead and anti-tuning protections | Unchanged |

The required minimum remains **>=709 valid sessions after exclusions**. It may
not be lowered, waived, averaged across datasets, or met by combining datasets.

## Superseded v0.1 data-governance clause

Only the v0.1 selection of its inadequate evaluation export, and the v0.1
prohibition on replacing that specific selected export, are superseded. The
v0.1 evaluation and confirmation files remain immutable historical records and
must not be edited, deleted, merged, reassigned, or used for a v0.2 replay.

This amendment does not make either v0.1 data file a valid v0.2 input.

## v0.2 predeclared data-selection plan

### Selection before inspection

Before the contents of either new raw export are opened, previewed, imported,
charted, parsed, structurally assessed, or used for research, the operator
must create one selection record containing all of the following:

1. The exact source: Exness `Exness-MT5Trial9` demo, `XAUUSDm`, M1.
2. The terminal-local export timezone and retrieval timestamp.
3. Exact start and end timestamps for one evaluation export and one later
   confirmation export.
4. The intended UTC coverage for both exports.
5. The source identity, acquisition method, and a statement that neither raw
   export has been viewed, assessed, or used to select a rule.
6. A declaration that the confirmation period is later than, and does not
   overlap, the evaluation period.
7. A declaration that neither period overlaps either v0.1 raw export or an
   already viewed Exness dataset.

The selection record is a data-governance record, not a performance result and
not a replay authorization.

### Evaluation dataset requirements

The v0.2 evaluation dataset must be a single, new, genuinely unseen Exness
`XAUUSDm` M1 export. It must not be a copy, subset, superset, appendage, merge,
or relabelling of either v0.1 raw export. It must be frozen and quality-assessed
as one dataset. A quality assessment may establish that it is inadequate, but
that finding does not permit another unrecorded replacement within v0.2.

The evaluation dataset may proceed to a replay-authorization review only when
its separately retained structural quality report establishes at least 709
complete qualifying sessions under the unchanged v0.2 rules.

### Confirmation dataset requirements

The v0.2 confirmation dataset must be a separate, later, genuinely unseen,
non-overlapping Exness `XAUUSDm` M1 export. It is reserved for independent
confirmation after, and only after, an authorized evaluation replay passes the
unchanged research gate.

The v0.1 confirmation export remains confirmation evidence for v0.1's frozen
data arrangement. It must not be reassigned as v0.2 evaluation data. Reuse is
prohibited because it would destroy role separation and because it is no longer
genuinely unseen.

## Freezing, manifesting, and access control

For each v0.2 raw export, before any row-level inspection:

1. Save the raw export directly into its role-separated restricted directory.
2. Record source, instrument, M1 timeframe, terminal-local source timezone,
   retrieval timestamp, and declared UTC coverage from the export operation.
3. Calculate and record SHA-256 from raw bytes only.
4. Create an immutable role-specific manifest and set the raw file and manifest
   owner-read-only.
5. Preserve a separate quality report that references the immutable raw-file
   SHA-256 without modifying the raw file or manifest.
6. Reject overlap with v0.1 evaluation, v0.1 confirmation, any other frozen
   research dataset, and any previously viewed Exness range.

The evaluation and confirmation exports must both be frozen, checksummed,
access-controlled, and role-assigned before either export's market-bar contents
are inspected.

## Continuing protections

The newly selected data may not be used to tune, invert, filter, select
parameters, change cost assumptions, revise session definitions, or choose a
favourable sample. The 08:25 decision remains limited to completed 08:20–08:24
information. Later bars, revised values, labels, outcomes, and all performance
results remain forbidden inputs to rule selection.

Independent confirmation remains mandatory after an evaluation pass. An
evaluation pass authorizes only the independent-confirmation study; it does not
authorize paper trading, MT5 execution, live trading, or a broker order.

## Authorization state

- [x] Candidate 002 v0.1 retained as an immutable historical specification.
- [x] Candidate 002 v0.2 data-governance amendment frozen.
- [ ] v0.2 evaluation and later confirmation selection record completed.
- [ ] v0.2 raw evaluation and confirmation exports frozen and manifested.
- [ ] v0.2 structural quality reports completed.
- [ ] Research approval authorizes deterministic v0.2 evaluation replay.
- [ ] Independent confirmation completed after an evaluation pass.
- [ ] Paper approval.
- [ ] Live approval.

## Non-authorization statement

This amendment changes no trading rule and grants no execution authority. It
does not authorize a replay, paper mode, MT5 order, broker order, optimization,
or performance inspection.
