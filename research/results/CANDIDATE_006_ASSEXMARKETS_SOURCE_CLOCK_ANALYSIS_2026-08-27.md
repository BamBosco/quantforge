# Candidate 006 — AssexMarkets source-clock analysis

Date: 2026-08-27. Dataset:
`data/candidate_006_second_broker/raw/XAUUSD_M1_202601020100_202608141159.csv`.

## Structural and continuity observations

- 217,842 rows across 160 observed dates.
- 173 source-clock gaps greater than one minute.
- The largest gap is 4,382 minutes, from 2026-04-02 23:58 to
  2026-04-06 01:00.
- The gap pattern includes recurring weekend/holiday closures; it must not be
  interpreted as a confirmed broker holiday calendar without broker authority.

## Spread by source-clock hour

| Hour | Rows | P50 | P95 | Maximum |
| --- | ---: | ---: | ---: | ---: |
| 01 | 9,598 | 9 | 25 | 214 |
| 02–05 | 9,598–9,600 | 9 | 19 | 50–64 |
| 06–09 | 9,600 | 8 | 19 | 50–79 |
| 10–11 | 9,593–9,600 | 8 | 19 | 47–64 |
| 12–18 | 9,510–9,540 | 8 | 19 | 30–36 |
| 19–20 | 9,362–9,479 | 8 | 19 | 30–31 |
| 21 | 9,307 | 8 | 19 | 358 |
| 22 | 9,189 | 8 | 19 | 33 |
| 23 | 8,197 | 8 | 25 | 214 |

These are source-clock statistics only. They do not identify New York, London,
Asia, rollover, or a broker session until the export clock's DST relationship
is authoritative.

## Current interpretation

The dataset supports a time-of-day spread analysis and confirms that the most
extreme spread observations cluster in source-clock hours 01, 21, and 23.
The historical P99.5 research value of 30 points remains a useful central
research cap, but the maximum of 358 and the live demo interval's 37 points
show why it must not be promoted as an unconditional execution limit.
