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

| Interpretation | Expected usual source open | Weekly exact matches | Structural assessment |
| --- | --- | ---: | --- |
| UTC+0 | Sunday 22:00 | 0/241 | Inconsistent |
| UTC+1 | Sunday 23:00 | 0/241 | Inconsistent |
| UTC+2 | Monday 00:00 | 1/241 | Inconsistent as a persistent clock |
| UTC+3 | Monday 01:00 | 235/241 | Best fixed-offset explanation; normal source close maps near 21:00 UTC |
| UTC+2 winter / UTC+3 summer (or another ordinary DST calendar) | 00:00 and 01:00 across sustained seasonal periods | Not observed | The five-day October 2025 shift reverses after one week, rather than persisting through winter |

The 194+ live EA time-provenance receipts independently establish current MT5
server UTC+3. Taken together, the full history and live receipts support this
limited inference: **the historical source clock is predominantly consistent
with UTC+3**. It remains an inference, not broker authority.

## Why this does not authorize UTC normalization

The one-week 2025 source-clock reversal occurs in the Europe/US DST-transition
period. It could reflect broker server-time behavior, an MT5 historical-feed
artifact, or another vendor scheduling rule. The CSV cannot distinguish those
possibilities. Applying fixed UTC+3 would silently move those bars by an hour;
applying a conventional DST zone would contradict the surrounding source-clock
pattern. The proper UTC-normalized evidence freeze therefore remains blocked
until AssexMarkets confirms both:

1. the XAUUSD MT5 server timezone and 2022–2026 DST schedule; and
2. that native MT5 Bars exports use that server clock.

## Policy effect

The source-clock inference strengthens the session-research hypothesis and
identifies the daily low-liquidity boundaries that need live coverage. It does
not promote the session policy, alter the provisional spread policy, establish
rollover, or authorize execution.

## External comparison source

CME's published gold-futures material describes a Sunday–Friday session with a
daily maintenance break. It is used only as the reference timing in this
structural comparison, not as an AssexMarkets specification:
https://www.cmegroup.com/trading/metals/files/fact-card-gold-futures-options.pdf
