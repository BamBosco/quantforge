# Candidate 006 — AssexMarkets XAUUSD 2026 bar evidence

This report concerns historical bars, not live observations or execution.  It
does not change any provisional XAUUSD production policy.

## Frozen source

- Dataset: `assexmarkets_global_demo_xauusd_m1_20260102_20260814`
- File: `data/candidate_006_second_broker/raw/XAUUSD_M1_202601020100_202608141159.csv`
- SHA-256: `45a24b5f53c5518f73a310800705ef0ce26036a8a315ee97c80073fb4bf85f33`
- Source: native MT5 Bars export, Assexmarkets Global Limited, server
  `AssexmarketsGlobal-Trade`, Demo Account — Hedge, symbol `XAUUSD`, M1.
- Exact terminal wall-clock range: 2026-01-02 01:00 through 2026-08-14 11:59.

Despite the export being described as “2026”, it ends on 14 August, so it is
not evidence for the whole calendar year.  The raw source was copied byte for
byte and its identity is recorded in the adjacent manifest.

The CSV contains no timezone or price-basis field.  Consequently timestamps
remain terminal wall-clock timestamps until an overlapping terminal/UTC sample
establishes server timezone and DST behaviour.  Price basis is likewise not
asserted from this export.  This is intentionally stricter than guessing from
the host clock or the current account.

## Structural and session quality

There are 217,842 bars over 160 trading dates.  Header fields include DATE,
TIME, OHLC, TICKVOL, VOL and SPREAD.  Validation found zero malformed rows,
duplicate timestamps, invalid OHLC rows, negative tick volumes, or negative
spreads.

112 inter-day gaps are 62 minutes, consistent with the observed 23:58 to 01:00
terminal schedule.  Most complete terminal dates contain 1,379 bars.  The
following dates are partial or have intraday omissions and must not be treated
as complete sessions: 2026-01-19, 2026-01-30, 2026-02-16, 2026-02-25,
2026-03-09 through 2026-03-27, 2026-04-08, 2026-05-25, 2026-06-01,
2026-06-19, 2026-07-03, 2026-08-11, and 2026-08-14.  Those include holidays,
short sessions, a March schedule change, and the export's final partial day;
the cause of each is not inferred from bars alone.

## Spread evidence (points, terminal bar field)

| Metric | Value |
| --- | ---: |
| Minimum / maximum | 0 / 358 |
| Mean | 10.859 |
| P01 / P05 / P50 | 7 / 7 / 8 |
| P90 / P95 / P99 | 19 / 19 / 30 |
| Bars at or above 30 | 3,694 |
| Bars at or above 100 | 30 |

The largest observed value (358 points) occurs around 2026-01-19 21:31–21:43
terminal time.  It is a stressed historical quote condition, not execution
slippage.  Hourly medians are 8–9 points; terminal-hour 01 has a 25-point P95
and 214-point maximum, and terminal-hour 23 has a 25-point P95 and 214-point
maximum.  This supports further broker-specific spread research and explicit
rollover/session sampling; it does not validate a maximum spread limit.

## Policy and evidence boundary

This dataset is broker-specific historical research evidence.  It is not
merged with Dukascopy observations, and it is not evidence of actual fills,
latency, rejected orders, execution deviation, or broker-authorized risk
limits.  The live authenticated AssexMarkets bridge remains the source for
append-only observed metadata and current quote provenance.  Before any policy
promotion, collect an overlapping server-time/UTC sample, a broader live quote
sample covering rollover and scheduled news, and read-only account/symbol
metadata; retain execution-policy fields as provisional unless genuine
paper/simulation evidence supports their evaluation.
