# ORB XAUUSD Headway Demo - Backtest Design

## Purpose

Test the approved, source-inspired ORB baseline without claiming that historical
futures observations transfer to Headway's XAUUSD CFD. This design evaluates a
narrow hypothesis before adding filters or broker execution.

## Fixed baseline

| Item | Rule |
|---|---|
| Instrument | Headway Demo `XAUUSD` |
| Session timezone | `America/New_York` |
| Opening range | High/low from 08:20:00 inclusive to 08:35:00 exclusive |
| Entry buffer | Ten-session Crabel `Stretch` |
| Entry | Buy stop at range high plus buffer; sell stop at range low minus buffer |
| Order handling | Orders form one OCO pair; first fill cancels the other |
| Stop | Long: range low minus buffer; short: range high plus buffer |
| Trade limit | One completed entry per session |
| Forced exit | Close any open position at 13:30 New York time |
| Filters | None |

`Stretch` for a session is the arithmetic mean over the previous ten completed
sessions of `min(abs(high - open), abs(open - low))`. It must use only sessions
available before the target session. Sessions with missing data are not silently
substituted; they are excluded and reported.

## Event sequence

```text
validate data -> construct range -> calculate prior-session Stretch
  -> create OCO entry intents -> Risk Engine approves/rejects
  -> simulate first executable fill -> cancel peer order
  -> monitor protective stop -> force session exit -> journal outcome
```

The backtest uses the same intent, risk-decision, order, and execution-outcome
contracts as future paper execution. A strategy never calculates a quantity or
sends an order directly.

## Data requirements

- UTC timestamps that can be converted unambiguously to `America/New_York`,
  including daylight-saving transitions.
- Prefer tick data; 1-minute bid/ask data is the minimum acceptable fallback.
- Bid/ask or explicit spread data, plus a recorded cost/slippage model.
- A documented data source, retrieval time, coverage, and dataset checksum.
- Enough prehistory for at least ten prior completed sessions before the first
  tested session.

The implementation must not use a broker server clock as a proxy for New York
time. It converts timestamps explicitly.

## Conservative fill rules

- A stop order can fill worse than its trigger price when a gap or available
  bid/ask implies it; favorable fills are not assumed.
- With OHLC bars that touch both the entry and stop in an unknowable sequence,
  the result is marked ambiguous and excluded from headline performance, unless
  tick data resolves the sequence.
- OCO cancellation is atomic in the simulator: after one fill, the peer cannot
  fill later in the same simulated event sequence.
- A trade is rejected when the calculated stop distance is zero, invalid, or
  violates the instrument's known stop level.
- A session is rejected when any M1 bar from 08:20 through the 13:30 exit is
  absent, duplicated, or lacks an explicit spread value.

## Research outputs

Each run records source dataset/version, code revision, configuration checksum,
timezone conversion, costs, rejected/ambiguous events, and all event-journal
records. Report total and annualized trades, win/loss distribution, expectancy
in R, maximum drawdown, exposure, profit factor, tail losses, and sensitivity
to spreads and slippage.

## Validation plan

1. Verify range and timezone boundaries with hand-checked sample sessions.
2. Run the fixed baseline on a predeclared in-sample period.
3. Run unchanged parameters on a held-out out-of-sample period.
4. Perform walk-forward and Monte Carlo analysis.
5. Test every future filter independently against the baseline.

No threshold for promotion to paper testing has been chosen. A positive result
does not authorize execution; promotion criteria and a forward-test runbook
require separate approval.
