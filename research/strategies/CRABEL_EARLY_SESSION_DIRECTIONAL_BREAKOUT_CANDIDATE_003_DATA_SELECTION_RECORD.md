# Candidate 003 — Frozen Pre-Inspection Data Selection Record

## Status

**Candidate ID:** `crabel_early_session_directional_breakout_candidate_003`

**Candidate version:** `0.1-draft-for-data-source-approval`

**Record version:** `0.1-frozen-pre-inspection`

**Status:** Frozen selection plan. This freezes only the selection plan; it
does not freeze Candidate 003's draft trading specification or authorize raw
data access, structural quality assessment, replay, paper mode, MT5 execution,
or broker orders.

No raw export was opened, previewed, parsed, imported, charted, structurally
assessed, replayed, or used to calculate strategy performance when creating
this record.

## Selection basis

The Dukascopy MT5 Bars interface has been observed offering `XAUUSD` M1 history
from `2019-08-01 01:05` through `2026-08-20 23:59`. The dates below are chosen
solely from that verified terminal availability boundary, chronological ordering,
and the need for a later independent confirmation period. No price behavior,
signal frequency, return, performance result, raw market bar, or quality result
was used.

Calendar coverage is not evidence of qualifying-session count. Both selections
remain subject to the unchanged requirement of at least 709 complete New York
08:20–13:30 sessions after a separately authorized structural-quality
assessment.

## Evaluation dataset predeclaration

| Field | Frozen value |
| --- | --- |
| Role | Evaluation |
| Venue/broker | Dukascopy Bank SA |
| Server/account environment | `Dukascopy-demo-mt5-1`; Demo Account — Hedge |
| Broker symbol | `XAUUSD` |
| Timeframe | M1 |
| Intended UTC coverage | `2019-08-01T00:00:00+00:00` through `2023-08-01T23:59:00+00:00` |
| Required source fields | Timestamp; bid open, high, low, close; per-bar recorded spread or equivalent sufficient to derive executable ask; tick volume; point/digits; volume minimum, maximum, and step; source/provenance; export timezone; retrieval metadata; instrument specification |
| Required New York session | Every M1 bar from 08:20 through 13:30 `America/New_York`; required-data faults are excluded without filling or inference |
| Minimum quality gate | >=709 complete qualifying sessions after exclusions |
| Provenance | Record terminal-local export timezone, retrieval time, terminal/server/account environment, exact symbol spelling, selection operation, and declared UTC coverage before raw-row inspection |
| Checksum | SHA-256 of raw bytes in a manifest before row-level inspection |
| Access control | Store only in a Candidate 003 evaluation-role restricted directory; raw export and manifest become owner-read-only when frozen |

## Confirmation dataset predeclaration

| Field | Frozen value |
| --- | --- |
| Role | Independent confirmation |
| Venue/broker | Dukascopy Bank SA |
| Server/account environment | `Dukascopy-demo-mt5-1`; Demo Account — Hedge |
| Broker symbol | `XAUUSD` |
| Timeframe | M1 |
| Intended UTC coverage | `2023-08-02T00:00:00+00:00` through `2026-08-20T23:59:00+00:00` |
| Required source fields | Same as evaluation: timestamp, bid OHLC, recorded spread or executable-ask equivalent, tick volume, point/digits, volume constraints, and complete provenance/timezone metadata |
| Required New York session | Every M1 bar from 08:20 through 13:30 `America/New_York`; unchanged exclusion rules apply without inference or filling |
| Minimum quality gate | >=709 complete qualifying sessions after exclusions |
| Independence | Later than and non-overlapping with evaluation; untouched until evaluation passes the frozen research gate and an independent confirmation authorization exists |
| Checksum | SHA-256 of raw bytes in a manifest before row-level inspection |
| Access control | Store only in a Candidate 003 confirmation-role restricted directory; raw export and manifest become owner-read-only when frozen |

## Chronology and contamination controls

Evaluation ends at `2023-08-01T23:59:00+00:00`; confirmation begins at
`2023-08-02T00:00:00+00:00`. The periods do not overlap. Evaluation is first
chronologically, while confirmation is later and remains untouched until a
separately authorized evaluation replay passes.

Candidate 001 and Candidate 002 raw data, manifests, confirmation data,
research results, and venue-specific conclusions are prohibited inputs to this
candidate. Neither a calendar date nor any market-data observation may be used
to alter Candidate 003's trading rules, select a subset, tune, invert, filter,
or change parameters.

The 08:25 decision in a later permitted replay may use only the completed
08:20–08:24 M1 observations for that New York date. Later bars, revised values,
labels, and outcomes are forbidden for the decision.

## Availability and unresolved quality facts

The intended periods lie within the terminal-export boundaries observed above.
The number of complete qualifying sessions is **UNKNOWN**. Calendar weekdays
must not be treated as qualifying sessions. Bid-OHLC, recorded-spread,
tick-volume, and timestamp-field sufficiency in the saved CSV is also
**UNKNOWN** until a separately authorized structural-quality assessment.

The terminal-local export timezone has not been verified. It must be recorded
at the export operation and preserved as provenance so timestamps can later be
normalized to UTC before converting to `America/New_York`. Do not assume that
the date controls in MT5 are UTC.

## Non-authorization statement

This record authorizes no confirmation export now, no structural assessment, no
replay, no performance calculation, no Candidate 004, no RuntimeStrategy, no
paper runner, no MT5 bridge/EA attachment, and no broker execution. Candidate
003 trading rules and Candidates 001 and 002 remain unchanged.
