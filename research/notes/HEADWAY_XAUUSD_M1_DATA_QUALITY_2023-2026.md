# Headway Demo XAUUSD M1 Data Quality Check — 2023–2026

## Provenance

- Export: `XAUUSD_M1_202308140101_202608141053.csv`
- Bars: 1,061,173 M1 bars
- Checksum:
  `488fa6147f1814b6671e67f853ed59d796e227b87c9f7004626ccd30fde7ace7`
- Mac timezone at export: `America/Los_Angeles`
- Normalized UTC range: 2023-08-14 08:01 through 2026-08-14 17:53

The MT5 Bars view was directly checked on 2026-08-14: its newest M1 row matched
the connected Mac clock exactly. Therefore the CSV uses the Mac timezone at the
time it is exported, not the broker chart-server timezone. This property is
recorded in the dataset manifest.

## Structural checks

| Check | Result |
| --- | ---: |
| Duplicate timestamps | 0 |
| Invalid OHLC relationships | 0 |
| Non-positive prices | 0 |
| Zero tick-volume bars | 0 |
| Zero exchange-volume rows | 1,061,173 |
| New York weekday sessions | 781 |

The exchange-volume column is zero throughout. Tick volume is available, but it
must not be represented as exchange-traded volume.

## ORB eligibility

The simulator requires an exact M1 sequence from 08:20 through 13:30 New York
time. It automatically excluded 25 dates with an incomplete required window.
Five additional dates had no complete opening range: 2024-03-29, 2025-01-01,
2025-04-18, 2026-01-01, and 2026-04-03. These are consistent with market
holidays and are not filled or guessed.

## Spread observations

| Measure | Points |
| --- | ---: |
| Minimum | 0 |
| Median | 23 |
| 95th percentile | 40 |
| 99th percentile | 54 |
| Maximum | 2,127 |

The spread tail is material. Every replay uses the recorded per-bar spread, and
the strategy result must also withstand separately declared adverse-slippage
scenarios.

## Decision

**Accepted for research replay only.** This dataset improves the sample size
substantially, but it remains M1 OHLC data rather than tick sequencing. It
cannot determine intrabar order, partial fills, or actual slippage.
