# Candidate 006 AssexMarkets XAUUSD M1 Historical Evidence

Date: 2026-08-26

## Dataset

- Broker: AssexMarkets
- Instrument/timeframe: XAUUSD / M1
- Raw filename: `XAUUSD_M1_202601020100_202608141159.csv`
- Raw size: 13,357,126 bytes
- SHA-256: `REDACTED_IN_REPOSITORY_REPORT; SEE PROVENANCE RECORD`
- Rows: 217,842
- Columns: `<DATE>`, `<TIME>`, `<OPEN>`, `<HIGH>`, `<LOW>`, `<CLOSE>`, `<TICKVOL>`, `<VOL>`, `<SPREAD>`
- Observed first source-clock timestamp: `2026-01-02 01:00:00`
- Observed last source-clock timestamp: `2026-08-14 11:59:00`
- Unique observed dates: 160, all weekdays, with 32 occurrences of each weekday.

## Provenance and timezone

The CSV contains no timezone field or broker-server metadata. The filename endpoints match the first and last row timestamps, but that establishes only the export-clock selection, not UTC.

AssexMarkets publicly states GMT+0 for its forex trading-hours table, but the available public material does not establish that the same timezone applies to this XAUUSD historical export. The analysis therefore does not assign a timezone or convert these timestamps to UTC.

Price fields have two decimal places. The raw `<SPREAD>` field is retained as the MT5 integer spread field. No monetary/pip conversion is asserted because the historical export does not contain authoritative XAUUSD point-size metadata.

## Validation

- Required MT5 fields: PASS
- Empty/null values: 0
- Duplicate timestamps: 0
- Timestamp regressions: 0
- Invalid OHLC rows: 0
- Negative tick volume: 0
- Non-positive tick volume: 0
- Negative spread: 0
- Zero spread rows: 8
- `<VOL>` is zero for every row and is not used as traded-volume evidence.
- Filename coverage agrees with observed first/last rows.

## M1 continuity

The recurring normal source-clock weekday shape is `01:00:00` through `23:58:00`, or 1,379 minutes. Against that observed weekday schedule, 2,798 bars are missing.

Important missing intervals include:

- 2026-01-19: 21:54–23:58, 125 bars
- 2026-02-16: 21:30–23:58, 149 bars
- 2026-03-12: 18:30–23:58, 329 bars
- 2026-05-25: multiple gaps totaling 127 bars before the end-of-day truncation
- 2026-06-19: 20:01–23:58, 238 bars
- 2026-07-03: 20:01–23:58, 238 bars
- 2026-08-14: 12:00–23:58, 719 bars because the export ends at 11:59

The March 9–27 period also contains repeated late-day truncation around 23:00–23:58 and smaller intraday gaps. These are data-continuity findings, not broker-session interpretations.

For the source-clock 08:20–13:30 window, 157 of 160 dates are complete. The incomplete dates are 2026-01-30, 2026-03-09, and 2026-08-14. This window cannot be relabelled as America/New_York until source timezone provenance is established.

## Tick volume

`<TICKVOL>` is populated and strictly positive on every row.

- Median: 262
- 95th percentile: 544
- 99th percentile: 760
- Maximum: 1,159

Tick volume is descriptive only and is not treated as centralized traded volume.

## Spread distribution

All figures are raw MT5 `<SPREAD>` integer points.

| Metric | AssexMarkets |
|---|---:|
| Median | 8 |
| 95th percentile | 19 |
| 99th percentile | 30 |
| 99.5th percentile | 30 |
| 99.9th percentile | 50 |
| Maximum | 358 |
| Zero-spread rows | 8 / 217,842 |
| Rows >30 points | 695 / 217,842 |
| Rows >50 points | 70 / 217,842 |
| Rows >100 points | 30 / 217,842 |

There are 89 contiguous source-clock runs above 30 points, totaling 695 bars. The largest is 494 minutes on 2026-03-02 from 01:06 through 09:19.

There are 36 runs above 50 points, totaling 70 bars. Eight runs exceed 100 points, totaling 30 bars. The largest stress episode is 2026-01-19 21:31–21:53 at 358 points.

The eight zero-spread records are isolated. Seven occur at the first 01:00 bar of a source-clock day; one occurs at 2026-02-04 18:48. They are not treated as proof of a genuinely zero-cost executable quote.

## Source-clock session behaviour

Most hours from 06:00 through 23:00 have a median spread of 8 points. The 01:00 hour has mean spread 12.57 points and 95th percentile 25. The 23:00 hour has mean 11.97 and 95th percentile 25.

This is source-clock behaviour only. It is not labelled as London, New York, Asia, rollover, or any other economic session.

## Dukascopy comparison

The existing frozen Dukascopy XAUUSD M1 replication covers 2023-08-02 through 2026-08-20, with recorded Africa/Lagos export timezone normalized to UTC and then evaluated in America/New_York. It has 772 valid complete New York weekday study sessions and an established 99.5th-percentile session spread of 760 points.

Assex historical evidence has a much lower raw spread distribution: 99.5th percentile 30 points and maximum 358 points. This is useful cross-venue historical evidence that the 760-point Dukascopy cap is not a universal XAUUSD spread requirement.

The comparison is deliberately limited to historical quote evidence. Assex source timezone is unresolved, so no session-aligned comparison is claimed. The contaminated old 8765 observation log is not used.

## Candidate 006 policy disposition

### Spread

**Better supported, broker-specific only.**

Assex historical evidence supports a research-only Assex cap around its historical 99.5th percentile of 30 raw points, while preserving the documented 358-point stress tail. This must not overwrite the Dukascopy 760-point evidence or become a universal broker-independent execution rule.

### Risk / maximum position

**Still provisional.**

Historical M1 bars do not establish account equity, margin, leverage, contract size, minimum volume, volume step, stop/freeze levels, or realized execution loss. The existing 0.10% simulated-trade budget and 0.01 maximum simulated volume therefore remain unchanged.

### Session

**Still provisional.**

The rows establish source-clock coverage only. The source timezone is not established, so the existing 08:20–13:30 America/New_York research window cannot be promoted to an Assex broker session from this CSV alone.

### Execution deviation

**Still provisional.**

Historical OHLC/spread data contains no order requests, fills, latency, rejects, quote-to-fill comparison, or slippage outcomes. The existing 0-point deviation rule remains a conservative research invariant, not broker execution evidence.

## Freeze status

The raw file has been copied into a separate owner-read-only local evidence package and SHA-256 recorded.

The normal QuantForge freeze utility requires authoritative UTC coverage. Because the Assex historical source timezone is not established, a false UTC-normalized manifest was deliberately not created.

Status:

- Raw-byte immutability: PASS
- Historical data quality assessment: PASS
- UTC-normalized evidence freeze: BLOCKED by unresolved source timezone
- Timezone guessing: NOT PERFORMED

## Execution evidence boundary

Historical bars do not establish fills, slippage, latency, rejects, or execution deviation. The independent Assex 8766 receipt collector remains the authoritative path for new broker-specific execution-quality evidence. The contaminated old 8765 log is excluded from this comparison.

## Remaining external requirements

1. Obtain authoritative AssexMarkets XAUUSD MT5 server/export timezone and DST behaviour for this historical export.
2. Confirm authoritative XAUUSD point size/digits/contract specification if spread conversion beyond raw MT5 points is required.
3. Continue the independent Assex 8766 receipt collector.
4. Obtain broker-authoritative XAUUSD trading hours, holidays, rollover and margin/volume rules if they are to become executable policy inputs.
5. Obtain real broker-specific execution evidence: order request time, quoted price, fill price, latency, slippage/adverse movement, rejection/retcode and reconciliation.
6. Re-run the normal QuantForge freeze workflow once timezone provenance is authoritative.

## Code/test status

No production code was required to interpret this dataset, so no production tests were changed for the analysis. A fresh full pytest/Ruff/strict-Mypy run was not claimed from this environment because the repository checkout is not mounted as an executable workspace here and the branch currently has no completed GitHub Actions run.