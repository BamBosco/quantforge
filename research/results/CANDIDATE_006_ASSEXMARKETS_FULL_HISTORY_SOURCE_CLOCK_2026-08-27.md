# Candidate 006 — AssexMarkets full-history source-clock inference

Dataset: `XAUUSD_M1_202201030100_202608141159.csv`.

This report derives structural inferences from a frozen native MT5 Bars export.
It does **not** replace broker documentation, establish an XAUUSD contract
session, or authorize a UTC-normalized replay.

## Frozen input and validation

| Field | Result |
| --- | --- |
| Source range | 2022-01-03 01:00 through 2026-08-14 11:59 source clock |
| Valid bar rows | 1,629,646 |
| SHA-256 | `22d471a693a204c227cfa53ed8798ca983d2699b075e26cc877dcaed2bf35875` |
| File size | 98,618,925 bytes |
| Duplicate/malformed/invalid-OHLC/negative-volume/negative-spread rows | 0 / 0 / 0 / 0 / 0 |
| Spread P50 / P95 / P99 / max | 5 / 15 / 20 / 1,126 raw MT5 points |

The raw export is retained unchanged under the second-broker raw-evidence
directory. `<VOL>` is zero in the native MT5 format and is not interpreted as
traded volume.

## Observed recurring structure

- 241 observed source-clock weeks.
- 235 weekly first bars are Monday 01:00. Five first bars are Tuesday 01:00
  on holiday-delayed weeks. One is Monday 00:00.
- 1,172 of 1,191 source dates begin at 01:00. The normal daily data span is
  approximately 01:00–23:54/23:58, followed by an approximately one-hour
  source-clock break.
- The first five bars of each source date have P50/P95/P99.5/max spreads of
  12/39/141/262 points. The last five have 11/28/145/975. These are
  low-liquidity boundary observations, not execution evidence.
- The source clock contains a material anomaly: 2025-10-27 through
  2025-10-31 each run from 00:00–22:58, whereas the surrounding weeks run
  01:00–23:58. It returns to 01:00 on 2025-11-03.

## Candidate-clock comparison

The comparison uses a **reference-only** gold-market boundary of about 22:00
UTC open and 21:00 UTC close, not an AssexMarkets-published XAUUSD schedule.
That reference is consistent with conventional COMEX gold session timing but
is not proof that the broker mirrors COMEX.

The scores below use the hourly first-bar boundary. The reference open is
22:00 UTC, so an offset of +3 predicts source-clock 01:00 and +2 predicts
00:00. This is an explicit structural scoring convention, not a claim that
AssexMarkets publishes that UTC session boundary.

| Interpretation | Expected usual source open | Daily first-bar fit | Weekly first-bar fit | Structural assessment |
| --- | --- | ---: | ---: | --- |
| UTC+0 | Sunday 22:00 | 0/1,191 (0.0%) | 0/241 (0.0%) | Inconsistent |
| UTC+1 | Sunday 23:00 | 0/1,191 (0.0%) | 0/241 (0.0%) | Inconsistent |
| UTC+2 | Monday 00:00 | 17/1,191 (1.4%) | 1/241 (0.4%) | Inconsistent as a persistent clock |
| UTC+3 | Monday 01:00 | 1,173/1,191 (98.5%) | 240/241 (99.6%) | Best fixed-offset explanation |
| Europe-style UTC+2 winter / UTC+3 summer | 00:00 in winter, 01:00 in summer | 708/1,191 (59.4%) | 143/241 (59.3%) | Rejected as a complete calendar model |
| US-style UTC+2 winter / UTC+3 summer | 00:00 in winter, 01:00 in summer | 782/1,191 (65.7%) | 158/241 (65.6%) | Rejected as a complete calendar model |

The 194+ live EA time-provenance receipts independently establish current MT5
server UTC+3. Taken together, the full history and live receipts support this
limited inference: **the historical source clock is predominantly consistent
with UTC+3**. It remains an inference, not broker authority.

## DST-anomaly investigation

The October 2025 anomaly is exact and internally consistent for both session
boundaries:

| Source-date range | First bar | Last bar | Interpretation status |
| --- | --- | --- | --- |
| 2025-10-20 through 2025-10-24 | 01:00 | 23:58 | Normal neighbouring week |
| 2025-10-27 through 2025-10-31 | 00:00 | 22:58 | Five sessions shifted exactly one hour earlier |
| 2025-11-03 through 2025-11-07 | 01:00 | 23:58 | Normal boundary resumed |

The affected week begins immediately after the European DST end on
2025-10-26 and ends immediately before the US DST end on 2025-11-02. That
timing is compatible with a DST-related interaction. It is not a confirmed
seasonal server-clock convention: the same Europe/US autumn transition windows
in 2022, 2023, and 2024 retain the normal 01:00 source open, and the historical
record returns to 01:00 after only five sessions rather than for a winter
season.

There is a second, different 2025 boundary anomaly. From 2025-03-10 through
2025-04-04, the first bar remains 01:00 while most daily last bars are 22:59;
the normal 23:58 close resumes on 2025-04-07. This coincides with the interval
between the 2025 US and European spring DST changes, but it changes only the
closing boundary. It therefore cannot establish a single timezone conversion
rule. Comparable historical gaps/early closes also occur around holidays and
feed interruptions.

The current live result and the dominant historical fit favor a UTC+3 research
hypothesis. The two 2025 discontinuities prevent treating it as year-round
server-clock proof. No fixed or ordinary Europe/US DST +2/+3 model explains
both the dominant pattern and these intervals.

## Why this does not authorize UTC normalization

The one-week 2025 source-clock reversal occurs in the Europe/US DST-transition
period, and the spring 2025 close-only change provides a second incompatible
pattern. They could reflect broker server-time behavior, an MT5 historical-feed
artifact, or another vendor scheduling rule. The CSV cannot distinguish those
possibilities. Applying fixed UTC+3 would silently move affected bars by an
hour; applying a conventional DST zone would contradict the surrounding
source-clock pattern. MetaQuotes documents that chart-bar time corresponds to
server time, while the current server clock is quote-derived; that does not
identify a broker's historical DST schedule. The proper UTC-normalized evidence
freeze therefore remains blocked until AssexMarkets confirms both:

1. the XAUUSD MT5 server timezone and 2022–2026 DST schedule; and
2. that native MT5 Bars exports use that server clock.

## Policy effect

The source-clock inference strengthens the session-research hypothesis and
identifies the daily low-liquidity boundaries that need live coverage. It does
not promote the session policy, alter the provisional spread policy, establish
rollover, or authorize execution.

On the **research-only UTC+3 hypothesis**, the usual source-clock 23:54/23:58
to 01:00 boundary maps approximately to 20:54/20:58 to 22:00 UTC. That is the
appropriate target interval for continued live spread collection, but must not
be configured as an approved broker rollover policy until the external evidence
above is obtained.

## External comparison source

CME's published gold-futures material describes a Sunday–Friday session with a
daily maintenance break. It is used only as the reference timing in this
structural comparison, not as an AssexMarkets specification:
https://www.cmegroup.com/trading/metals/files/fact-card-gold-futures-options.pdf

MetaQuotes documents that `TimeCurrent()` returns last-known server time and
that chart/bar time corresponds to server time:
https://www.mql5.com/en/docs/dateandtime/timecurrent
https://www.mql5.com/en/articles/599
