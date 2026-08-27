# Candidate 006 — AssexMarkets cross-instrument MT5 clock analysis

Date: 2026-08-27. This is a read-only broker-infrastructure analysis. EURUSD
is used only to test common MT5 clock behaviour; it is not a Candidate 006
instrument and its forex schedule is not transferred to XAUUSD.

## Evidence and method

The analysis reads the immutable payloads persisted by the authenticated local
bridges. EURUSD results are filtered by the database `broker_symbol` column.
Seven earlier XAUUSD receipts were found in the EURUSD database before the EA
symbol switch; they are preserved as evidence but excluded from EURUSD counts.
For each receipt with a complete `time_provenance` object, it compares
the EA's `terminal_server_time` with its `terminal_utc_time`. The latter equals
the accepted receipt event time for the fresh receipts considered here.

| Stream | Database | Accepted receipts at analysis | Provenance receipts | Broker server |
| --- | --- | ---: | ---: | --- |
| XAUUSD | `data/candidate_006_second_broker/mt5_observations.sqlite3` | 711 | 426 | `AssexmarketsGlobal-Trade` |
| EURUSD | `data/assexmarkets_eurusd/mt5_observations.sqlite3` | 177 | 177 | `AssexmarketsGlobal-Trade` |

The two databases remain separate. No observation was routed through a broker
order endpoint, and no position or fill is inferred from these quotes.

## Current cross-instrument clock result

| Instrument | Exact +180-minute server-minus-UTC result | Within one minute of +180 | Result |
| --- | ---: | ---: | --- |
| EURUSD | 177/177 | 177/177 | Uniform current MT5 UTC+3 |
| XAUUSD | 402/426 | 402/426 | Fresh/current observations support MT5 UTC+3 |

All 177 clean EURUSD receipts have a server-minus-UTC offset of exactly 180
minutes; their terminal-local-minus-UTC offset is exactly 60 minutes. For
XAUUSD, 402 of 426 receipts are within one minute of +180 minutes, including the current
healthy run. The remaining 28 receipts occur in an earlier interrupted/stale
quote interval and range from about +165 to +179 minutes. `TimeCurrent()` is
the time of the last quote received by the terminal rather than a local clock;
therefore those non-fresh values are retained as provenance evidence but are
not a competing server-time regime. The current conclusion is scoped to the
observed August 2026 trade-server state: **both instruments on
`AssexmarketsGlobal-Trade` currently report MT5 server time UTC+3.**

This is stronger than a single-instrument conclusion: the identical offset is
present across FX and metals in the same MT5 server/account environment. It
does not establish a historic offset or broker DST rule.

## Relation to the frozen XAUUSD historical export

The native source-clock CSV remains unchanged and frozen at SHA-256
`22d471a693a204c227cfa53ed8798ca983d2699b075e26cc877dcaed2bf35875`.
Its recurring structure is best explained by a fixed UTC+3 hypothesis:

| Historical test | Fixed UTC+3 fit | Meaning |
| --- | ---: | --- |
| Daily first-bar boundary | 1,173/1,191 (98.5%) | Best fixed-offset fit |
| Weekly first-bar boundary | 240/241 (99.6%) | Best fixed-offset fit |

The live cross-instrument result corroborates the *current* endpoint of that
historical inference. It does not resolve the five-session 2025-10-27 through
2025-10-31 shift to source 00:00–22:58, or the incompatible 2025 spring
close-only anomaly. Neither an ordinary Europe nor US UTC+2/UTC+3 seasonal
model fits the complete export. A fixed UTC+3 conversion would move the
affected bars by an unproven hour; a conventional DST conversion contradicts
the predominant historical structure. **No UTC-normalized historical derivative
or freeze is authorized.**

The remaining unknown is not the current live offset. It is the broker's
historical server/export convention for 2022–2026, specifically whether those
anomalies are an MT5 historical-feed artifact, an instrument schedule rule, or
a broker server/DST change. Only dated broker confirmation or archived
time-provenance at a DST boundary can distinguish them.

## Published GMT+0 forex schedule versus observed MT5 UTC+3

AssexMarkets' forex page says its forex hours are Sunday 21:05–Friday 20:59,
labels those timings "server time (GMT+0)", and states forex swaps occur at
21:00 GMT+0. The same page does not identify the MT5 server name, terminal
clock API, historical Bars-export basis, or an XAUUSD schedule.

That wording conflicts with the observed current MT5 `AssexmarketsGlobal-Trade`
UTC+3 clock. The evidence does **not** establish why. Defensible possibilities
include a published schedule convention that is distinct from the MT5 trade
server clock, a page that is stale/inaccurate for this MT5 environment, or a
separate platform/account schedule convention. None may be silently selected.
The direct EA data is authoritative for the current observed MT5 clock; the
broker page remains the only published FX schedule statement and requires
broker clarification before it is used for either FX timing or XAUUSD policy.

MetaQuotes documents that `TimeCurrent()` is formed on the trade server and is
the last known quote time, which explains why freshness is required when
interpreting it. It does not provide the broker's historic timezone/DST policy.

## Session and policy effect

- **EURUSD weekly/daily behaviour:** 172 Thursday intraday receipts span about
  seventy-one minutes. They confirm quote availability and M1-bar capture but
  contain no Friday close, Sunday/Monday open, daily break, rollover, or DST
  boundary. No weekly/daily schedule conclusion is available yet. XAUUSD's
  five newly restored receipts are likewise ordinary Thursday observations.
- **XAUUSD session policy:** remains provisional. The UTC+3 hypothesis is now
  cross-instrument corroborated, but the historical DST/export relationship,
  XAUUSD hours, rollover, and holiday calendar are not authoritative.
- **Spread policy:** remains broker-specific research-supported and
  provisional. The historical 30-point P99.5 is central research evidence;
  the historical 1,126-point tail and live XAUUSD spreads show it cannot be an
  unconditional execution cap. EURUSD quotes provide no XAUUSD spread policy
  evidence.
- **Risk/max position:** remains provisional. Broker-observed XAUUSD contract
  metadata is not an approved risk mandate or stable tiered-margin schedule.
- **Execution deviation:** remains partially evidenced and provisional. The
  prior manual demo round trip is genuine but is not a distribution; the
  read-only EURUSD and XAUUSD receipts cannot create latency, rejection, or
  fill-deviation evidence.

## Required external evidence

1. AssexMarkets confirmation naming the `AssexmarketsGlobal-Trade` MT5 server
   timezone and its historical 2022–2026 DST schedule, including the October
   2025 interval.
2. Confirmation that native MT5 Bars exports use that server clock.
3. Broker-authoritative XAUUSD trading hours, rollover and holiday schedule.
4. Continued isolated EURUSD coverage through its daily break, weekly
   open/close and a DST boundary, if FX schedule verification is desired.

## Sources

- https://www.assexmarkets.com/forex-cfd
- https://www.mql5.com/en/docs/dateandtime/timecurrent
- `research/results/CANDIDATE_006_ASSEXMARKETS_FULL_HISTORY_SOURCE_CLOCK_2026-08-27.md`
