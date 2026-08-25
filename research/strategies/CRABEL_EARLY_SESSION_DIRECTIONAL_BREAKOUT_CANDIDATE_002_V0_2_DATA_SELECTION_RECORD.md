# Candidate 002 v0.2 — Pre-Inspection Data Selection Record

## Status

**Candidate ID:** `crabel_early_session_directional_breakout_candidate_002`  
**Candidate version:** `0.2-frozen`  
**Record type:** Pre-inspection evaluation/confirmation data-selection record  
**Status:** Frozen selection plan. No raw export has been created, opened,
previewed, parsed, imported, charted, structurally assessed, replayed, or used
to calculate strategy performance.

This record implements the data-selection procedure in Candidate 002 v0.2. It
does not modify Candidate 002 v0.2, grant replay authorization, or create a new
candidate.

## Selection basis

The selected periods are based only on protocol and data-availability facts:

- Candidate 002 requires at least 709 valid sessions after exclusions.
- Four calendar years contain 1,045 Monday--Friday dates in each selected
  period, providing a predeclared calendar buffer above the 709-session gate.
- Existing frozen Exness Candidate 002 v0.1 metadata occupies evaluation
  coverage through `2023-08-11T20:57:00+00:00` and confirmation coverage from
  `2023-08-13T22:05:00+00:00` through `2026-08-20T23:59:00+00:00`.
- The v0.2 periods begin after that frozen coverage and are chronologically
  ordered evaluation first, confirmation later.

No strategy performance, returns, signal frequency, market behavior, price
series, raw bar, or quality-assessment result was used to choose these dates.

## Evaluation dataset predeclaration

| Field | Predeclared value |
| --- | --- |
| Role | Evaluation |
| Venue/server | Exness `Exness-MT5Trial9` demo |
| Broker symbol | `XAUUSDm` |
| Timeframe | M1 |
| Intended UTC coverage | `2026-08-24T00:00:00+00:00` through `2030-08-23T23:59:00+00:00` |
| Terminal-local export timezone | Record at export time; do not change it between range selection and export |
| Time normalization | Preserve raw source facts; record the terminal-local timezone and normalize timestamps to UTC in the later, separately authorized structural-quality process |
| Required market fields | M1 bid OHLC, per-bar recorded spread, tick volume, point size, digits, volume minimum, maximum, and step; source/provenance, export timezone, retrieval metadata, and instrument specification |
| Required session | Every M1 bar from 08:20 through 13:30 `America/New_York`; missing, duplicate, malformed, crossed, spreadless, stale, or clock-regressed required data is excluded without inference or filling |
| Minimum quality gate | At least 709 complete qualifying sessions after exclusions |
| Provenance | Record Exness server, account environment, exact symbol spelling, acquisition method, export-operation timestamps, and declared coverage before raw-row access |
| Checksum | SHA-256 of raw bytes, recorded in an immutable manifest before row-level inspection |
| Access control | Role-separated restricted directory; raw export and manifest owner-read-only after freeze |

## Confirmation dataset predeclaration

| Field | Predeclared value |
| --- | --- |
| Role | Independent confirmation |
| Venue/server | Exness `Exness-MT5Trial9` demo |
| Broker symbol | `XAUUSDm` |
| Timeframe | M1 |
| Intended UTC coverage | `2030-08-26T00:00:00+00:00` through `2034-08-25T23:59:00+00:00` |
| Terminal-local export timezone | Record at export time; do not change it between range selection and export |
| Time normalization | Preserve raw source facts; record the terminal-local timezone and normalize timestamps to UTC in the later, separately authorized structural-quality process |
| Required market fields | M1 bid OHLC, per-bar recorded spread, tick volume, point size, digits, volume minimum, maximum, and step; source/provenance, export timezone, retrieval metadata, and instrument specification |
| Required session | Every M1 bar from 08:20 through 13:30 `America/New_York`; apply the unchanged Candidate 002 exclusions without inference or filling |
| Independence | Later than and non-overlapping with the evaluation dataset; reserved for confirmation only after an authorized evaluation replay passes |
| Checksum | SHA-256 of raw bytes, recorded in an immutable manifest before row-level inspection |
| Access control | Role-separated restricted directory; raw export and manifest owner-read-only after freeze |

## Chronological separation and anti-contamination

The evaluation period ends on `2030-08-23T23:59:00+00:00`. The confirmation
period starts on `2030-08-26T00:00:00+00:00`, the following Monday. There is no
temporal overlap. The confirmation export is later in time and must remain
unopened and unused until an authorized evaluation replay has passed the
unchanged Candidate 002 research gate.

The frozen Candidate 002 v0.1 confirmation export remains a confirmation-role
record for v0.1. It is not an input to this v0.2 record and may not be
reassigned as evaluation data.

## Frozen-range overlap check

This check used manifest metadata only; no raw market-data rows were accessed.

| Existing frozen range | Relationship to v0.2 evaluation | Relationship to v0.2 confirmation |
| --- | --- | --- |
| v0.1 evaluation: `2019-01-02T00:00:00+00:00` to `2023-08-11T20:57:00+00:00` | No overlap | No overlap |
| v0.1 confirmation: `2023-08-13T22:05:00+00:00` to `2026-08-20T23:59:00+00:00` | No overlap | No overlap |

## Availability and uncertainty

At the time of this record, Exness MT5 history has been observed only through
`2026-08-20`. Neither predeclared v0.2 period is available for export yet.
The calendar counts of 1,045 weekdays per period establish expected calendar
capacity above 709 sessions, but do not establish actual session completeness.
Only a later, separately authorized structural-quality report may determine the
number of qualifying sessions.

## Next manual export action

No export action is authorized now because the selected periods are not yet
available. When the full predeclared evaluation period has become available,
the next permitted action is a direct MT5 Bars M1 export for exactly the
evaluation UTC coverage recorded above, saved directly to the restricted
evaluation directory without opening or previewing the raw file. The later
confirmation export is not performed until its independently predeclared
coverage is available.

## Non-authorization statement

This selection record does not authorize structural quality assessment, replay,
optimization, strategy modification, paper mode, MT5 execution, or a broker
order. Candidate 002 trading rules remain unchanged.
