# Candidate 004 — Vantage MT5 Evaluation Structural/Data-Feasibility Report

## Scope and controls

**Candidate identifier:** `candidate_004`  
**Dataset assessed:** `data/candidate_004_vantage_mt5_raw/evaluation/XAUUSD_M1_VantageMarkets_Demo_201301020000_202312292356.csv`  
**Evaluation manifest:** adjacent `.manifest.toml` sidecar  
**Assessment type:** source/data structural feasibility only; no strategy exists or was used.

Only the evaluation CSV and its evaluation manifest were read. The confirmation
CSV was not opened, previewed, parsed, checksummed, or otherwise accessed. The
raw evaluation CSV and its manifest were not modified.

## Decision

**FAIL — the frozen evaluation artifact is not a homogeneous M1 dataset across
its declared 2013–2023 terminal-time range.** It is not suitable as the frozen
Candidate 004 evaluation dataset in its present form. This is a data-acquisition
finding, not a strategy or performance result.

Historical source-time/DST mapping also remains unresolved, which independently
prevents a research-calendar freeze in `America/New_York`.

## Schema and representation

The tab-delimited header exactly contains:

`<DATE>`, `<TIME>`, `<OPEN>`, `<HIGH>`, `<LOW>`, `<CLOSE>`, `<TICKVOL>`,
`<VOL>`, `<SPREAD>`.

The timestamp is the combination of `<DATE>` and `<TIME>`, formatted as
`YYYY.MM.DD HH:MM:SS`. There is no offset, timezone label, or UTC designation
in the CSV. The manifest likewise identifies terminal-origin data but declares
the historical server DST convention `UNKNOWN`.

## Actual coverage and granularity

| Finding | Result |
| --- | --- |
| All raw timestamps | `2013.01.02 00:00:00` through `2023.12.29 23:56:00` |
| Total parsed rows | 1,875,397 |
| Distinct terminal dates | 2,839; Monday–Friday only |
| Daily-bar section | 1,346 one-row dates, `2013.01.02`–`2018.03.16` |
| Sub-M1/hourly-like section | 128 dates, `2018.03.19`–`2018.09.13`; mostly 23 rows/date (range 19–183) |
| M1-density section | `2018.09.14`–`2023.12.29`; 1,870,956 rows across 1,365 terminal dates |

The filename and manifest describe an M1 export, but the first roughly five
years are daily data and the following roughly six months are not M1-dense.
The requested 2013–2023 range therefore cannot be treated as one M1 history.

## Price precision and volume fields

All OHLC strings use two decimal places. The observed price lattice supports a
minimum representable increment of **0.01** in this export. This demonstrates
CSV precision only; it does not by itself establish the broker's contractual
tick size.

`<TICKVOL>` is non-zero on 1,875,336 rows and zero on 61. `<VOL>` is zero on
all 1,875,397 rows, so no usable real-volume series is supplied.

## Bid, ask, and spread availability

There are no separate bid or ask OHLC columns, and neither the CSV nor manifest
identifies which side the OHLC values represent. `<SPREAD>` is present and is
non-zero on 1,858,275 rows and zero on 17,122 rows. It may be useful as a
recorded spread field after later validation, but this export alone cannot
reconstruct ask OHLC/high/low or independently establish bid/ask availability.

## Structural integrity findings

| Check | Result |
| --- | --- |
| Malformed rows / parse errors | 0 / 0 |
| Timestamp ordering violations | 0 |
| Duplicate timestamps | 0 |
| Invalid OHLC relationships | 0; every row satisfies `low ≤ open/close ≤ high` |
| Observed short gaps in M1-density section | 223 gaps of 2–59 minutes, totaling 604 omitted minutes between adjacent records |
| Longer gaps in M1-density section | 1,369 gaps of 60+ minutes, including recurring 62/63-minute and multi-day gaps |

The gaps are documented structural facts only. This assessment does not assign
them to a broker cause, holiday, maintenance, or trading rule.

## Calendar and session capacity

Terminal-date weekday population across the entire file is: Monday 566,
Tuesday 571, Wednesday 569, Thursday 572, Friday 561, and no Saturday/Sunday
dates. This is source-terminal calendar capacity only, not a New York research
calendar.

In the M1-density portion, 1,363 of 1,365 dates have at least 1,000 records;
1,303 have at least 1,370 records; and 1,028 have exactly 1,378 or 1,379
records. No terminal date has 1,440 records. There are 1,331 uninterrupted
one-minute runs of at least 1,000 minutes. These figures indicate potential
generic M1 continuity only; no eventual strategy-specific window has been
defined, and no qualifying-session count is calculated.

## Timezone/DST conclusion and New York mapping

The only direct offset evidence is the separately recorded live observation of
UTC+3 on 24 August 2026. It is outside this evaluation file's time range. The
CSV/manifest do not provide an offset or DST rule. The raw historical terminal
schedule also does not establish a single, evidenced all-history conversion
rule.

Accordingly, no defensible timestamp-to-`America/New_York` conversion is
available from the authorized evidence. For this report, every CSV timestamp is
retained as `source_terminal_time` and deliberately left unmapped. Assuming
UTC, UTC+2, UTC+3, Lagos time, or New York time would exceed the evidence.

## Remaining blockers

1. Replace or re-acquire the 2013–2018 portion as genuine M1 data if that
   historical period is required.
2. Establish an evidence-supported historical source-time/DST convention before
   freezing a New York research calendar.
3. Determine, in a separately authorized structural assessment, whether the
   spread field is complete and whether source-side bid/ask information can be
   supplied for any future execution model.
4. Establish a future strategy-specific required window only after the data and
   calendar issues are resolved.

No strategy rules, signals, returns, trades, backtests, optimization, tuning,
or trading-related execution were performed.
