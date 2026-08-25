# Strategy Runtime Integration Contract

## Purpose and approval boundary

This contract is the minimum evidence and interface package required before a
strategy may implement `RuntimeStrategy` and be connected to the paper runtime.
It does not approve a strategy. Research approval and paper approval are
separate, immutable references and must both exist before integration.

## Required strategy package

The strategy package must supply all of the following.

| Requirement | Required content |
| --- | --- |
| Identity | Immutable strategy ID and version; source revision/hash; owner. |
| Scope | Canonical instruments, broker-symbol mapping, permitted account, market venue, and paper-only authority. |
| Research | Research approval reference, frozen specification reference, validation report, predeclared data split, costs, and acceptance gates. |
| Paper approval | Explicit paper-approval reference, effective date, expiry/review rule, and permitted runtime configuration hash. |
| Data | Required fields, source, price side, freshness limit, bar/tick completeness, spread requirements, and invalid-data behavior. |
| Time | Required timeframe(s), timezone, session/calendar rules, DST treatment, and allowed evaluation cadence. |
| Signals | Deterministic signal ID, rationale, instrument, side, entry price, protective stop, optional target, and maximum signal frequency. |
| Execution | Market or conditional-entry semantics, trigger price, OCO grouping, ambiguity rule, expiry, cancellation rule, and one-entry/session rule where applicable. |
| Risk | Protective SL requirement for every entry, TP policy if used, scheduled exits, maximum holding period, and risk-reservation requirements for conditional groups. |
| Replay | No-lookahead declaration, point-in-time data requirements, deterministic replay procedure, expected event ordering, and idempotency behavior. |

## `RuntimeStrategy` interface

The implementation must satisfy [runtime.py](../src/quantforge/strategies/runtime.py):

```python
class RuntimeStrategy(Protocol):
    strategy_id: str

    def evaluate(
        self, market: MarketFact, *, evaluated_at: datetime
    ) -> TradingSignal | None: ...
```

The strategy may emit a signal or no signal. It may not size, approve, submit,
cancel, modify, journal, or execute an order. The Risk Engine alone sizes and
approves; `PaperRuntimeHost` and `PaperExecutor` own paper lifecycle handling.

## Signal and entry constraints

- `strategy_id` must match the approved immutable ID/version.
- Instrument and side must be in approved scope; side is `buy` or `sell`.
- Entry and stop prices must be positive and form a protective stop on the
  adverse side of entry. Target is optional but must be explicit when present.
- Signal IDs must be deterministic from the frozen point-in-time inputs. A
  replay must not create a different signal for the same observation.
- The maximum signal frequency and duplicate suppression key must be declared.
- Conditional entries must declare stop trigger, OCO group, expiry, peer
  cancellation, ambiguity handling, and reservation of maximum—not summed—risk.

## Data integrity and no-lookahead

The strategy must return no signal when required data is stale, missing,
duplicate, malformed, outside its session, or unavailable at `evaluated_at`.
It may use only information available at that point in time. Forming bars,
future bars, revised data, future event outcomes, and post-session labels are
forbidden unless the frozen specification explicitly permits and timestamps
them.

## Integration acceptance test

Before connection, an approval review must verify that a supplied strategy:

1. satisfies the interface and emits no execution instructions;
2. reproduces its predeclared signals under deterministic replay;
3. rejects invalid/out-of-session data without a signal;
4. respects its frequency, session, SL/TP, and conditional-order declarations;
5. produces journaled intent, risk decision, and paper outcomes through the
   strategy-neutral runtime; and
6. has neither MT5 execution access nor live-trading authority.
