# ORB Decision Sheet

## Status

**Baseline approved for backtest design.** This remains a research
specification, not an approved strategy for paper or live trading.

## Recommended first experiment

Use the simplest source-inspired baseline first: one instrument, one defined
session, an opening range, two-sided breakout entry with OCO cancellation, one
protective stop, one trade maximum, and a time-based session exit. Test feature
filters separately; do not combine them initially.

## Decisions

| Decision | Choices / definition | Owner selection |
|---|---|---|
| Market and instrument | Exact broker symbol and asset class | **Headway Demo `XAUUSD` for paper testing** |
| Session | Exchange session and IANA timezone; FX requires an explicitly chosen session because it has no single central open | **08:20-13:30 `America/New_York`** |
| Opening range | 5, 15, or 30 minutes, measured from session open | **15 minutes: 08:20-08:35** |
| Breakout buffer | Crabel-style rolling `Stretch`; fixed ticks/points; or volatility-normalized buffer | **Source-style ten-session Stretch** |
| Entry | Stop order above/below range plus buffer; OCO cancellation on first fill | **Approved** |
| Direction | Two-sided baseline, then separate directional-bias experiment | **Two-sided** |
| Stop loss | Defined before approval; initial candidate: opposite side of range or a predeclared volatility stop | **Opposite range side plus the same buffer** |
| Exit | Session close; fixed R multiple; trailing stop; or separately tested scale-out | **13:30 `America/New_York` market exit** |
| Maximum trades | One completed entry per instrument/session | **One** |
| Early-entry filter | None for baseline; 5-minute early-move hypothesis as a separate experiment | **Proposed: none** |
| Other filters | Inside day/NR7, gap, volume, VWAP, trend, news/calendar | **None in baseline** |
| No-trade conditions | Invalid/stale data, abnormal spread, missing session bar, risk halt, or unavailable symbol | **Proposed** |
| Risk sizing | Risk Engine only; research results reported in normalized R and realistic costs | **Required** |

## Required data and test design

- Point-in-time 1-minute OHLCV or tick data for the selected venue and session.
- Instrument specification, tick size, contract/lot value, spreads, fees,
  slippage, and session calendar.
- A predeclared in-sample, out-of-sample, and walk-forward period.
- Separate experiments for each proposed filter and parameter family.
- A fill model that handles stop-order gaps, partial fills, OCO races, and
  non-tradable periods.

## Broker profile boundary

The profiles below are different instruments for research and configuration;
they must never share assumed contract specifications or historical datasets.

| Account profile | Symbol | Permitted use at this stage |
|---|---|---|
| Headway Demo | `XAUUSD` | Paper-testing candidate |
| Exness Standard | `XAUUSDm` | Future separate configuration profile only |
| Exness Cent | `XAUUSDc` | Future separate configuration profile only |

Before a profile can be used, record its MT5 Symbol Specification: server
timezone, trading sessions, contract size, minimum/maximum/step volume, point,
tick size, tick value, stop level, margin/leverage, swap, and typical/maximum
spread. A screenshot of an H4 chart is insufficient for these controls.

### Headway Demo XAUUSD - recorded specification

The current specification is stored in
[`config/brokers/headway_demo.toml`](../../config/brokers/headway_demo.toml).
It records a 100-XAU contract per lot, 0.01 minimum/step volume, two price
digits, floating spread, market execution, and weekday broker sessions from
01:05 through 23:58. Spread and margin are dynamic runtime inputs; they are not
hardcoded. The broker chart-server timezone remains unconfirmed. MT5 Bars CSV
timestamps are recorded in each dataset manifest using the Mac timezone at
export time; they must not be treated as broker-server timestamps.

## Approval gate

The baseline is documented in
[the configuration profile](../../config/strategies/orb_xauusd_headway_demo_baseline.toml)
and [backtest design](ORB_BACKTEST_DESIGN.md). Offline, non-sized backtest
simulation is approved. Paper and live strategy execution remain prohibited
until the validation and promotion gates are separately approved.
