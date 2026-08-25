# Candidate 006 XAUUSD — Stage A and Readiness Evidence Assessment

## Decision

**Candidate 006 remains a read-only, non-executable observation and audit
path.  Stage A and readiness are not eligible to be configured yet.**

This assessment records the boundary after live XAUUSD bridge evidence became
available.  It does not create a risk policy, a trade intent, a Stage-A
request, a readiness marker, or any order capability.

## Evidence classes

### Broker-observed facts

The read-only bridge accepted schema-v2 XAUUSD observations from the Dukascopy
demo runtime and appended matching Candidate 006 audit rows.  A fresh verified
receipt linked `observation_event` 330 to isolated audit record 7.  The audit
records native broker facts including point, digits, contract size, volume
bounds and step, filling mode, stop and freeze levels, tick values, currencies,
and trade-calculation mode.

The currently recorded facts are runtime observations, not policy parameters.
In particular, a current `stop_level` or `freeze_level` of zero does not prove
that either value will remain zero, nor does it create a permissible distance
or execution rule.

### Repository-derived research evidence

The versioned Headway Demo XAUUSD M1 dataset is accepted for replay research
only.  Its spread distribution is materially tailed (median 23 points, 95th
percentile 40, 99th percentile 54, maximum 2,127) and it is explicitly not
tick sequencing or fill evidence.  It therefore cannot set a Dukascopy spread
limit or execution-deviation limit.

The XAUUSD intraday-volatility study now has a checksum-verified, cross-venue
Dukascopy replication: 772 valid sessions after the documented zero-spread
exclusions, with 16.05% development and 24.73% holdout MAE reductions.  This
resolves the offline volatility-replication evidence item only.  It does not
establish direction, position size, risk budget, execution quality, or
paper-trading authority.

The historical directional ORB and intraday-momentum candidates did not supply
a promoted XAUUSD directional strategy.  No approved strategy therefore
exists to which a maximum exposure or session policy could be attached.

### Live-observation sufficiency

At assessment time, the live runtime log contained 316 accepted XAUUSD events
from about 3 hours of one trading session.  Recorded spreads ranged from 400
to 2,350 points (mean about 1,118).  That is useful broker telemetry, but it
does not cover declared eligible sessions, normal and stressed conditions, or
enough independent days to select a risk threshold.

### Model and calendar evidence

The local Ollama endpoint was unavailable during this assessment.  In addition,
the existing Qwen3/Ollama research adapter is explicitly a non-executable
USDJPY workflow: its final-intent schema accepts only `USDJPY`.  No model
output was generated or treated as XAUUSD evidence.

The repository contains a versioned XAUUSD USD-tier-1 scheduled-event policy,
but no economic-calendar provider adapter or immutable provider snapshot has
yet been supplied.  Scheduled-event protection cannot be claimed operational
without that audited input.

## Unresolved requirements and required evidence

| Requirement | Why it remains unresolved | Minimum evidence before promotion |
| --- | --- | --- |
| Maximum spread policy | The historical distribution is from Headway, while the live sample is only one partial Dukascopy session. | Immutable, receipt-linked Dukascopy spread observations across predeclared sessions and independent days; a predeclared threshold selection and adverse-spread validation. |
| Risk-sizing formula and maximum position | No promoted directional XAUUSD strategy, approved risk budget, or capital/exposure mandate exists. Broker volume bounds are constraints, not an exposure policy. | A separately reviewed XAUUSD risk specification tied to a promoted strategy, account-equity basis, stop-distance formula, aggregate-exposure rule, and adverse-loss validation. |
| Trading-session policy | Manual broker-session screenshots lack a durable server-time mapping, and no promoted strategy defines eligible XAUUSD windows. | Broker-observed session/timezone provenance plus a predeclared strategy-session study covering normal, rollover, holiday, and scheduled-event treatment. |
| Execution deviation | Read-only observations contain quotes but no fill, latency, reject, or slippage outcomes. | Non-live, reproducible execution-quality evidence with defined reference price, latency window, adverse movement/slippage scenarios, and broker-specific validation. |
| Stop/freeze handling | Current values are observed dynamically, but no policy says how a request must respond if they change. | A fail-closed runtime rule and tests that bind each request to fresh observed values; this follows, rather than replaces, the missing strategy and sizing evidence. |
| Scheduled-event control | The policy has no provider-backed, immutable calendar input. | A provider adapter mapping immutable IDs to canonical events, stored snapshots, freshness enforcement, and tests. |

## Policy-evidence disposition after Dukascopy replication

The replication raw export contains 772 complete New York 08:20–13:29 session
windows with positive recorded M1 spreads.  Within those windows, the observed
spread-point distribution is: median 297, 90th percentile 506, 95th percentile
567, 99th percentile 700, and maximum 3,690.  These are descriptive historical
bar values, not fills or contemporaneous quote acceptance outcomes.  They do
not justify choosing a maximum-spread threshold, because no promoted XAUUSD
strategy specifies its cost tolerance or adverse-spread response.

The same data establishes that the study window can be observed across many
New York weekdays.  It does not establish a trading-session policy: it has no
durable broker trading-hours contract, rollover/holiday handling, or strategy
eligibility rule.

The receipt-linked read-only evidence contains broker contract facts and
quotes, but no orders, fills, latency, rejection, or slippage result.  It
therefore cannot support an execution-deviation policy.  Broker lot bounds
likewise remain implementation constraints rather than a risk budget or
maximum-position mandate.

Accordingly, no XAUUSD spread, session, risk/exposure, or execution-deviation
configuration is created by this update.  Each remains deliberately
fail-closed, and Candidate 006 remains ineligible for Stage A.

## Stage A boundary

`MT5StageAExecutionGateway` is already a data-only, unsendable request
constructor.  Its configuration loader deliberately accepts only the USDJPY
Candidate 005 profile.  It must not be repurposed for XAUUSD by copying USDJPY
risk, spread, session, or deviation values.

An XAUUSD Stage-A profile can be designed only after every applicable row above
has independently satisfied its promotion evidence.  It must retain
`live_trading_enabled = false`, `order_submission_enabled = false`, and the
`prohibited_stage_a` submission status.

## Readiness boundary

The existing readiness guard has the explicit scope
`candidate_005_usdjpy_one_demo_order`.  It cannot evidence or authorize
Candidate 006.  A future Candidate 006 readiness design requires a validated
XAUUSD Stage-A request, fresh accepted XAUUSD snapshot, approved deterministic
risk result, XAUUSD-specific one-position/account checks, and the outstanding
policy evidence above.  It must remain an unclaimed, non-executable marker.

## Next permitted action

Collect the listed evidence under immutable provenance and update the relevant
policy through the existing validation and review path.  The receipt-linked
live collection command is:

```zsh
PYTHONPATH="$PWD/src" .venv/bin/python tools/export_candidate_006_evidence.py \
  --observations data/mt5_observations.sqlite3 \
  --audit data/candidate_006_xauusd/xauusd_m1_demo.sqlite3 \
  --destination data/candidate_006_xauusd/<new-evidence-package>
```

It accepts only schema-v2, accepted XAUUSD receipts whose independently stored
Candidate 006 audit payload exactly matches the bridge receipt; it freezes a
JSONL package and SHA-256 manifest without deriving policy.  Independent
historical confirmation data must continue through the existing
`freeze_research_dataset.py` raw-export procedure.  Until then,
`config/candidate_006_xauusd_read_only.toml` must retain every unresolved
requirement and Candidate 006 must remain fail-closed.
