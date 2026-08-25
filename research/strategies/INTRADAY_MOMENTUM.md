# Intraday Momentum — Strategy Specification

## Status

**Experiment 001 rejected and frozen on 2026-08-14.** See the
[research result](../results/INTRADAY_MOMENTUM_XAUUSD_HEADWAY_DEMO_M1_REPLAY_2026-08-14.md).
The strategy and replay code exist for auditability only; neither is approved
for confirmation, paper trading, or live trading.

This is a deliberately minimal, price-only hypothesis. It is not a claim that
momentum exists in Headway Demo `XAUUSD`. It does not reuse the rejected ORB
entry mechanism and does not add indicators, volume, or news filters.

See the [candidate decision](INTRADAY_MOMENTUM_CANDIDATE.md) and
[source review](../papers/INTRADAY_MOMENTUM_SOURCE_REVIEW.md).

## Research question

After the direction of the first 30 minutes of the chosen New York session is
known, does holding that same direction until the defined afternoon exit have a
positive, cost-robust distribution for Headway Demo `XAUUSD`?

### Null hypothesis

The initial 30-minute direction has no useful predictive value after recorded
spread and adverse slippage; any apparent performance is noise.

## Fixed market and calendar

| Item | Definition |
| --- | --- |
| Venue and instrument | Headway Demo `XAUUSD` |
| Strategy timezone | `America/New_York` |
| Eligible days | New York weekdays with complete, valid required M1 data |
| Signal window | 08:20:00 inclusive through 08:50:00 exclusive (30 completed M1 bars) |
| Entry time | 08:50:00 New York M1 bar open |
| Forced exit | 13:30:00 New York M1 bar open |
| Maximum completed entries | One per eligible session |

The 30-minute duration is selected before testing because the reviewed
intraday-momentum literature commonly studies early-session return intervals.
The 08:20 start and 13:30 exit are retained from the already documented XAUUSD
research session so the experiment introduces one new strategy type rather
than a simultaneous session search.

## Deterministic signal and entry

1. Let `signal_open` be the bid open of the 08:20 bar.
2. Let `signal_close` be the bid close of the completed 08:49 bar.
3. If `signal_close > signal_open`, generate one **buy market intent** at the
   08:50 bar open.
4. If `signal_close < signal_open`, generate one **sell market intent** at the
   08:50 bar open.
5. If the prices are equal, or any required M1 bar is missing, duplicate,
   invalid, or lacks recorded spread, record **no trade** with the reason.

For a buy, the simulated entry is the 08:50 bid open converted to ask using the
recorded 08:50 spread, plus adverse slippage. For a sell, the simulated entry
is the 08:50 bid open minus adverse slippage. There is no limit order, stop
entry, averaging, or second attempt.

## Protective stop and exit

| Position | Protective stop |
| --- | --- |
| Buy | Lowest bid low of the 08:20–08:49 signal window |
| Sell | Highest ask high of the 08:20–08:49 signal window, using the recorded per-bar spread |

The stop must be strictly on the loss side of entry. If it is not, the Risk
Engine rejects the non-sized intent. An open position exits at its protective
stop or at the 13:30 forced exit, whichever occurs first. Same-M1 entry/stop
touches are ambiguous with M1 data and must be excluded rather than assumed.

## Costs and data controls

- Use the immutable Headway Demo XAUUSD M1 dataset manifest and its recorded
  source-timezone conversion.
- Use recorded per-bar spread plus fixed adverse slippage of 0, +1, and +3
  points. These scenarios are sensitivity tests, not asserted actual fills.
- Require every M1 bar from 08:20 through 13:30. Missing or duplicate required
  data excludes the session and is recorded.
- Do not use true VWAP, order flow, exchange volume, or order-book inputs.
- Scheduled news/event policy remains separate and is not added to this first
  attribution test.

## Risk assumptions and limits

- Results are normalized R only. The strategy never supplies a quantity,
  account value, leverage, or dollar P&L.
- A future live or paper version can emit only a trade intent with entry and
  stop; the Risk Engine remains sole authority for approval, sizing, cancels,
  and flattening.
- No target, trailing stop, scale-out, reversal, or re-entry is allowed.

## Validation and failure gate

- Run the strategy exactly once with the versioned configuration and the
  standard chronological validation protocol.
- Report every eligible, rejected, no-trade, ambiguous, stopped, and forced
  exit session.
- The experiment must pass all protocol requirements across all three cost
  scenarios before it may enter independent confirmation work.
- A failure freezes the specification. Parameter sweeps, threshold tuning, or
  adding filters to rescue it are prohibited.
- Passing still does not authorise paper or live trading.

## Result and freeze

The approved replay was run once under the standard chronological protocol and
failed all-cost-scenario development performance and walk-forward requirements.
Its positive holdout segment does not override those failures. The complete
result is retained in the [research report](../results/INTRADAY_MOMENTUM_XAUUSD_HEADWAY_DEMO_M1_REPLAY_2026-08-14.md).

This specification is frozen. It must not be tuned, supplemented with filters,
or promoted to any trading environment.
