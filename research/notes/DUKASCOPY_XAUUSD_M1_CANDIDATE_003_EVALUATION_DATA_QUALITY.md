# Dukascopy XAUUSD M1 Structural Quality Assessment — Candidate 003 Evaluation

This is a structural data-quality assessment of the frozen Candidate 003
evaluation export only. It does not calculate a strategy signal, simulate an
entry or exit, calculate R, evaluate returns, optimize, or inspect
profitability. The confirmation dataset was not accessed.

## Frozen-file integrity

| Check | Result |
| --- | --- |
| Dataset | `data/candidate_003_research_unseen/evaluation/XAUUSD_M1_201908010105_202308012354.csv` |
| Manifest | `dukascopy_demo_mt5_1_xauusd_m1_20190801_20230801.manifest.toml` |
| Manifest SHA-256 | `7942acbdafb1343a8d42032d8048a6f43ecc9b7e8df03fab40908b18dc3635ef` |
| Recomputed SHA-256 | `7942acbdafb1343a8d42032d8048a6f43ecc9b7e8df03fab40908b18dc3635ef` |
| Integrity result | Match — PASS |

## Dataset and timestamp facts

| Item | Result |
| --- | --- |
| ROWS | 1,404,394 raw rows; all parseable under the observed MT5 schema |
| Timestamp format | `<DATE>` `YYYY.MM.DD` plus `<TIME>` `HH:MM:SS` |
| Declared source timezone | `Africa/Lagos` / WAT (`UTC+01:00`), from immutable manifest |
| UTC normalization | Apply `Africa/Lagos`, then convert to UTC before `America/New_York` |
| UTC COVERAGE | `2019-08-01T00:05:00+00:00` through `2023-08-01T22:54:00+00:00` |
| NEW YORK COVERAGE | `2019-07-31T20:05:00-04:00` through `2023-08-01T18:54:00-04:00` |

## Required fields and metadata

| Requirement | Finding |
| --- | --- |
| Bid OHLC | PASS — `<OPEN>`, `<HIGH>`, `<LOW>`, `<CLOSE>` are present; chart mode was independently recorded as bid price |
| Recorded spread / executable ask model | PASS — `<SPREAD>` is present per bar; direct ask OHLC is not present, so later executable ask derives from bid plus recorded spread under the fixed rules |
| Tick volume | PASS — `<TICKVOL>` is present |
| Additional volume field | `<VOL>` is present; it is not required for the non-sized study |
| Timestamp provenance | PASS — source timezone, server/source, retrieval timestamp, and selected UTC coverage are in the frozen manifest |
| Instrument identity | PASS — manifest records `XAUUSD`, Dukascopy MT5 Demo source, and acquisition method |
| Point/digits and volume constraints | Not stored in this dataset manifest. They are separately recorded from the verified Dukascopy Symbol Specification: 3 digits; 0.01 minimum and step; 10,000 maximum; 1,000 limit. This is a manifest metadata limitation, not a raw-row/session failure. |

## Structural checks

The eligible population is every Monday–Friday New York date from 2019-07-31
through 2023-08-01: **1,045 calendar weekdays**. Each date was tested for every
M1 timestamp from 08:20:00 through 13:30:00 New York inclusive (311 expected
minutes), after `Africa/Lagos → UTC → America/New_York` conversion.

| Check | Result |
| --- | --- |
| Malformed timestamp, OHLC, spread, or tick-volume rows | 0 |
| Non-positive or invalid/crossed OHLC rows | 0 |
| Missing or negative spread rows | 0 |
| Zero recorded-spread rows | 39,738 — retained as explicit recorded values, not missing values |
| Negative or zero tick-volume rows | 0 |
| Non-minute-aligned timestamps | 0 |
| Global duplicate timestamps | 0 |
| Duplicate timestamps in a required session | 0 |
| Clock-regressed source-order transitions | 0 |
| Stale-data determination | No provider stale flag or frozen staleness threshold exists. Required-window gaps are counted as missing bars; no independent stale classification was inferred. |

## Session result

| Item | Result |
| --- | --- |
| COMPLETE QUALIFYING SESSIONS | **1,010** |
| INCOMPLETE SESSIONS | **35** |
| EXCLUSION BREAKDOWN | `missing_required_minutes`: 35 sessions; all other exclusion reasons: 0 sessions |
| 709-SESSION REQUIREMENT | **PASS** — 1,010 >= 709 (surplus: 301 sessions) |
| RESULT | **PASS — structurally eligible evaluation dataset** |

The 35 incomplete eligible New York dates are:

`2019-07-31`, `2019-12-25`, `2020-01-01`, `2020-04-10`, `2020-04-13`,
`2020-05-07`, `2020-10-13`, `2020-12-25`, `2021-01-01`, `2021-01-15`,
`2021-01-25`, `2021-02-26`, `2021-03-23`, `2021-03-26`, `2021-04-02`,
`2021-05-31`, `2021-06-15`, `2021-06-16`, `2021-06-18`, `2021-09-07`,
`2021-09-24`, `2021-10-14`, `2021-12-24`, `2021-12-27`, `2022-01-20`,
`2022-03-21`, `2022-04-15`, `2022-09-02`, `2022-09-07`, `2022-10-11`,
`2022-12-26`, `2023-01-02`, `2023-02-27`, `2023-04-07`, `2023-06-26`.

No trading signal, trade, return, R value, or performance measure was computed.
The evaluation dataset is structurally eligible; the next governance step is to
freeze Candidate 003's research authorization before any replay. This report
does not itself authorize replay, confirmation access, paper mode, MT5
execution, or live trading.
