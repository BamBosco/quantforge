# Candidate 005 — USD/JPY Evaluation Structural Data-Feasibility Report

**Candidate ID:** `candidate_005`  
**Scope:** evaluation-only structural validation  
**Decision:** **FAIL — the saved evaluation artifact is not genuine M1 data.**

## Authority and file binding

Only the following evaluation file was read for this report:

`/Users/mac/Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/users/user/Documents/USDJPY_M1_201908010000_202308012300.csv`

| Fact | Value | Status |
| --- | --- | --- |
| File size | 331,508 bytes | VERIFIED |
| SHA-256 | `ca9dd4bcdb5307b52cac55a34c6667b83277dddc540fb95258613f33b02bee22` | VERIFIED |
| Companion acquisition manifest beside file | Not present under the expected `.manifest.toml` / `.manifest.json` names | VERIFIED |
| Confirmation dataset | Not accessed, listed, checksummed, opened, previewed, parsed, or otherwise touched | VERIFIED |
| Strategy, replay, backtest, optimization, tuning, performance, or trading | Not performed | VERIFIED |

The CSV was not modified. No acquisition or replay authorization is created by
this report.

## 1. Exact CSV schema

| Item | Finding | Status |
| --- | --- | --- |
| Delimiter | Tab | VERIFIED |
| Header | `<DATE>`, `<TIME>`, `<OPEN>`, `<HIGH>`, `<LOW>`, `<CLOSE>`, `<TICKVOL>`, `<VOL>`, `<SPREAD>` | VERIFIED |
| Timestamp representation | Separate date and time fields, parsed as `YYYY.MM.DD` plus `HH:MM:SS` | VERIFIED |
| OHLC fields | `<OPEN>`, `<HIGH>`, `<LOW>`, `<CLOSE>` | VERIFIED |
| Volume fields | `<TICKVOL>`, `<VOL>` | VERIFIED |
| Spread field | `<SPREAD>` | VERIFIED |
| Price decimal representation | Exactly three decimal places in every OHLC value | VERIFIED |
| Smallest observed price grid | `0.001` | VERIFIED |

## 2. Timestamp provenance

| Finding | Status |
| --- | --- |
| Actual first timestamp string | `2019-08-01 00:00:00` — VERIFIED |
| Actual last timestamp string | `2023-08-01 23:00:00` — VERIFIED |
| Ordering | Ascending — VERIFIED |
| Timestamp timezone/basis | `UNKNOWN` — the CSV contains no UTC/GMT offset or timezone label, and no companion acquisition manifest establishes it. |
| Conversion to `America/New_York` | Not performed — PENDING source-time provenance. |

The filename and timestamp strings do not prove GMT/UTC. They must not be
treated as UTC or New York time.

## 3. BID/ASK and spread provenance

| Finding | Status |
| --- | --- |
| Native side represented by OHLC | `UNKNOWN` — the CSV header has no BID/ASK marker and the available acquisition metadata does not establish it. |
| Spread-field completeness | 5,315 of 5,315 rows have a numeric `<SPREAD>` value — VERIFIED |
| Spread-field validity for execution modelling | Not sufficient — all 5,315 values are zero; minimum = maximum = `0` — VERIFIED |
| Derivable executable bid/ask spread | Not possible from this file — VERIFIED |
| Separate native ASK acquisition needed for a defensible future model | Yes, together with an explicitly identified native BID M1 extract and exact UTC matching — PENDING future acquisition; it must not be acquired under this report. |

A separate ASK extract would not repair this artifact's non-M1 structure.
Any future acquisition must obtain the correct M1 data first.

## 4. Structural data quality

| Check | Finding | Status |
| --- | --- | --- |
| Data rows, excluding header | 5,315 | VERIFIED |
| Malformed rows | 0 | VERIFIED |
| Invalid timestamps | 0 | VERIFIED |
| Duplicate timestamps | 0 | VERIFIED |
| OHLC rows with missing values | 0 | VERIFIED |
| Invalid OHLC relationships | 0 | VERIFIED |
| Adjacent one-minute timestamp steps | 0 | VERIFIED |
| Adjacent gaps greater than one minute | 5,314 of 5,314 adjacent steps | VERIFIED |
| Most common adjacent interval | 60 minutes: 4,420 occurrences | VERIFIED |
| Other observed intervals | 1,440 minutes: 683; 4,320 minutes: 171; 2,940 minutes: 37; also 2,880, 5,760, and 360 minutes | VERIFIED |
| Genuinely M1 throughout | No — FAIL |

The file is mixed frequency. It contains 893 calendar dates with one record,
148 dates with 24 records, 37 dates with 23 records, and one date with 19
records. The denser portion is hourly rather than M1. Its M1 filename is not
supported by its timestamp sequence.

## 5. Calendar/session observations only

| Observation | Finding | Status |
| --- | --- | --- |
| Unique calendar-date strings | 1,079 | VERIFIED |
| Weekday date strings | 1,042 | VERIFIED |
| Weekend date strings | 37, all Saturdays | VERIFIED |
| Strategy-specific complete-session capacity | Cannot be established | PENDING — timestamp basis is unknown and M1 coverage is absent. |
| Existing validation-protocol capacity | Cannot be established | PENDING — raw weekday count is not a count of complete protocol sessions. |

These are raw timestamp-string observations only; they do not assign research
dates, New York sessions, or strategy eligibility.

## Comparison with Candidate 005 requirements

| Requirement | Result | Status |
| --- | --- | --- |
| USD/JPY historical source | Dukascopy MT5 artifact present | VERIFIED |
| Intended M1 evaluation data | File is daily/hourly mixed frequency | FAIL |
| UTC/GMT timestamp provenance | Not established | PENDING |
| Defensible bid/ask or spread representation | Side unknown and recorded spread is uniformly zero | FAIL |
| Exact requested coverage endpoint | Ends at `23:00:00`, not the initially proposed `23:59:00` | VERIFIED discrepancy |
| Row-level integrity within available rows | No malformed, duplicate, invalid-timestamp, or invalid-OHLC rows found | VERIFIED |

## Conclusion

This saved evaluation artifact is technically valid as a tabular MT5 export,
but it **fails Candidate 005's data-feasibility requirements for a future M1
research dataset**. The failure is source-file selection/frequency and
execution-provenance related; it makes no statement about USD/JPY market
behavior or any strategy.

No corrective acquisition is authorized here. A future governance step would
need to supersede this file for intended M1 use, pin the actual M1 period and
UTC/GMT basis, and require a defensible native BID/ASK representation before a
new evaluation artifact could be acquired.
