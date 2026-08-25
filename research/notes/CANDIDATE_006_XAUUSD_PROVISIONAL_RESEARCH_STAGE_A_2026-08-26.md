# Candidate 006 XAUUSD — Provisional Research Stage A

## Decision

Candidate 006 may construct **data-only, unsendable research Stage A
artefacts** under `candidate_006_xauusd_research_stage_a.toml`. This is not an
execution, paper-order, readiness, broker-session, or production-policy
approval. Order submission remains disabled in every path.

## Evidence-backed facts

- The verified Dukascopy M1 replication has 772 complete positive-spread New
  York study sessions. Its session-window spread distribution has a 99.5th
  percentile of 760 points.
- Receipt-linked Dukascopy observations establish the XAUUSD contract's 0.01
  minimum volume and volume step, plus a USD demo account with $10,000 observed
  equity at collection time.
- There are no XAUUSD fills, reject codes, latency samples, slippage outcomes,
  broker-authoritative session hours, or calendar-provider snapshots.

## Provisional research parameters

| Area | Parameter | Value | Rationale and expiry |
| --- | --- | ---: | --- |
| Spread | Maximum accepted quote spread | 760 points | Historical 99.5th-percentile rejection cap; not an execution estimate. |
| Risk | Per-simulated-trade budget | 0.10% of observed equity | Owner-directed research cap; $10 against the observed $10,000 demo equity. |
| Exposure | Maximum simulated volume | 0.01 | One observed broker minimum volume/step. |
| Session | Research window | 08:20–13:30 America/New_York weekdays | Existing study window only; not broker trading hours. |
| Deviation | Accepted price deviation | 0 points | No execution evidence exists; exact quote matching is required. |

All parameters expire for review at `2026-09-02T00:00:00Z`. The loader rejects
any changed cap or any attempt to enable live trading, order submission, or a
Stage A send action.

## Hard safety invariants

- `live_trading_enabled = false`
- `order_submission_enabled = false`
- `stage_a_send_allowed = false`
- every constructed artefact has `send_allowed = false` and
  `submission_status = "prohibited_stage_a"`
- a non-executable, approved risk decision is required;
- quoted spread must be positive and no greater than 760 points;
- simulated volume must not exceed 0.01;
- research construction is rejected outside the weekday study window, after
  review expiry, or unless the intent exactly matches the current bid/ask.

## Remaining external evidence for any executable promotion

An execution-capable Stage A still requires an approved directional strategy,
reviewed risk/exposure mandate, broker-authoritative sessions and calendar
input, plus real broker-specific execution-quality evidence. None is implied
or replaced by this research-only configuration.
