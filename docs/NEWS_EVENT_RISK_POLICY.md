# Scheduled News and Event Risk Policy

## Status

**Research foundation implemented. Not connected to a calendar vendor or
execution venue, not approved for paper trading, and not applicable to a live
account.**

The local foundation includes versioned policy configuration, vendor-neutral
calendar snapshots, fail-closed blackout decisions, and immutable audit-event
contracts. A provider adapter, durable journal integration, paper-execution
adapter, and operational runbook remain required.

This policy protects capital around scheduled events that can cause exceptional
spread widening, gaps, price jumps, rejected orders, and unreliable fills. It
is a Risk Engine control, not a predictive trading signal and not a strategy
filter owned by ORB.

## Core rule

For every covered high-impact event affecting an instrument:

1. Start a blackout **three hours before the scheduled event time**.
2. At blackout start, the Risk Engine rejects all new trade intents for the
   affected instrument.
3. The execution layer cancels all unfilled entry orders for that instrument.
4. Any open position for that instrument is closed at the best available market
   price no later than the blackout start. The closure must be journaled with
   the event identity, the planned cutoff, actual execution time, and outcome.
5. No new entry is permitted until the event blackout has ended under a
   separately approved post-event policy. Until then, the default is a manual
   operator release.

The automated policy does **not** wait for a losing position to recover before
closing it. Waiting has no known time limit and can increase loss during the
highest-risk period. It contradicts the purpose of a pre-news risk limit.

## Initial XAUUSD event scope

For Headway Demo `XAUUSD`, the initial covered event catalogue is scheduled,
USD-related Tier 1 releases and meetings, including:

- FOMC policy-rate decisions, statements, minutes when scheduled, and press
  conferences;
- U.S. Employment Situation / non-farm payroll release;
- U.S. Consumer Price Index (CPI) release;
- U.S. Personal Consumption Expenditures (PCE) price-index release; and
- U.S. GDP release.

The final event catalogue must be represented by stable provider event IDs,
country, currency, importance tier, and scheduled UTC timestamp—not informal
event names matched from a webpage. A future research review may add or remove
categories only through a versioned configuration change and independent
testing.

## Time, data, and failure safety

- Store every event in UTC, retain the source timezone and provider timestamp,
  and calculate the three-hour cutoff from the scheduled UTC time.
- Use an independent, reliable economic-calendar data provider behind a
  QuantForge adapter. MT5 chart data is not a calendar source.
- Persist an immutable calendar snapshot and its source/version with every
  research run and every Risk Engine decision.
- Refresh the schedule before the trading session and monitor corrections,
  cancellations, and newly scheduled events while the system is active.
- If the calendar feed is missing, stale, malformed, or internally
  contradictory, reject new affected-instrument intents and cancel unfilled
  entry orders. Raise an operator alert immediately.
- A feed failure must never cause the system to guess an event time. If an
  already-open position has no verified cutoff, it requires an explicit,
  journaled Risk Engine emergency decision; it must not be left open under an
  automatic “wait for recovery” rule.

Scheduled calendars cannot protect against unscheduled headlines, geopolitical
events, outages, or liquidity shocks. Existing stop-loss, spread, drawdown,
and kill-switch controls remain necessary.

## Required architecture

```text
Calendar provider -> Calendar validation -> Event-risk policy -> Risk Engine
                                                        |              |
                                                        |              +-> reject intents
                                                        +-> execution -> cancel / flatten
                                                                       |
                                                                  audit journal
```

The implementation uses, or will add, these isolated boundaries:

| Boundary | Responsibility |
| --- | --- |
| Calendar provider port | Retrieve event IDs, scheduled times, revisions, and importance from one vendor without leaking vendor types into the domain. |
| Calendar validation | Validate schema, UTC conversion, revision ordering, staleness, and instrument/event mapping. |
| Event-risk policy | Compute blackout state from a versioned policy and validated calendar observations. |
| Risk Engine | Reject affected new intents; it remains the sole authority for the decision. |
| Execution adapter | Act only on Risk Engine-approved cancel/flatten commands; report actual outcomes. |
| Audit journal | Retain source snapshot, policy version, cutoff calculation, decision, and execution result. |

Strategy code must never query an economic calendar directly, cancel its own
orders, or flatten its own positions.

## Research and testing requirements

Before this policy can enter paper testing:

- Acquire event history with stable identifiers and revisions suitable for
  historical replay.
- Test calendar timezone conversions, daylight-saving changes, revised events,
  same-day multiple events, outages, stale feeds, duplicate events, and events
  during an open position.
- Simulate the pre-event closure using conservative spread and slippage; do
  not assume a normal market fill near a major event.
- Measure the policy separately from ORB Experiment 002. Adding it to that
  experiment would combine two unvalidated changes and invalidate attribution.
- Define a post-event re-entry policy and paper-operating runbook before it is
  allowed to release an instrument automatically.

## Non-negotiable limits

- No machine-learning model will decide whether a scheduled event is safe.
- No “close only if profitable” or “wait until the loss is smaller” exception.
- No new position may bypass an active event blackout.
- No execution adapter may receive a direct strategy request to cancel or
  flatten an order.
