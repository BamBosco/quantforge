# Headway Demo XAUUSD M1 Data Quality Check — 2026-08-14

## Scope and provenance

This is a structural data-quality check, not a strategy-performance result.

- Export: `XAUUSD_M1_202605050405_202608140952.csv`
- Bars: 99,872 one-minute bars
- Export range in broker-server time: 2026-05-05 04:05 through 2026-08-14 09:52
- Normalized UTC range: 2026-05-05 09:05 through 2026-08-14 14:52
- SHA-256: `51a8bf300863451412445f367022a96c2fb34f51633f92c2bfd788b301ec5741`
- Source timezone: `America/Los_Angeles` (Mac timezone at export time)

The Bars export itself was verified on 2026-08-14 to use the connected Mac's
local clock: its newest M1 row matched the Mac time exactly. The file covered
only the May-to-August daylight-saving period; source timezone is still a
per-export property and must not be inferred from a broker chart clock.

## Structural results

| Check | Result |
| --- | --- |
| Duplicate timestamps | 0 |
| Invalid OHLC relationships | 0 |
| Non-positive price bars | 0 |
| Zero tick-volume bars | 0 |
| Zero exchange-volume column | 99,872 (all rows) |
| ORB 08:20–08:34 New York windows missing a minute | 0 of 74 export dates |

The `VOL` column is zero throughout, which is expected for many broker CFD
feeds. Research may use MT5 tick volume, but must not label it exchange volume.

## Session coverage and gaps

The stated regular broker session is 01:05–23:58. A complete M1 export contains
1,373 bars because the final one-minute bar starts at 23:57 and closes at 23:58.
Of 72 interior weekday dates, 64 have all 1,373 expected bars.

The first and last dates are expected partial exports. The following shortened
dates should be classified as special-session candidates and verified against a
Headway trading calendar before they are used in a normal-session comparison:

| Date | Bars | Observed last bar | Notes |
| --- | ---: | --- | --- |
| 2026-05-25 | 1,166 | 20:30 | likely holiday/special session |
| 2026-06-19 | 1,136 | 20:00 | likely holiday/special session |
| 2026-07-03 | 1,135 | 20:00 | likely holiday/special session; also one missing minute at 06:57 |

Observed isolated or short-block omissions total 24 minutes. The largest is an
18-minute interruption on 2026-07-14 between 11:52 and 12:03 broker time.
Other single-minute omissions occur on 2026-05-05, 2026-06-08, 2026-06-12,
2026-07-03, 2026-07-13, and 2026-08-07.

## Spread and volume observations

The export’s spread is in points (one point is 0.01 for this symbol).

| Measure | Points |
| --- | ---: |
| Median spread | 33 |
| 95th percentile | 37 |
| 99th percentile | 44 |
| Maximum | 459 |

The maximum spread is a material outlier. A future simulation must consume the
recorded per-bar spread or apply conservative spread/slippage assumptions; it
must not substitute a single average spread.

## Decision

**Accepted for importer integration and ORB-window plumbing only.** It is not
adequate evidence that the strategy has an edge: the sample is roughly three
months, uses M1 bars rather than tick sequencing, includes special sessions,
and has a small number of gaps. The backtester must exclude or explicitly label
special/gapped sessions and mark intrabar order-sequence ambiguity instead of
inventing fills.
