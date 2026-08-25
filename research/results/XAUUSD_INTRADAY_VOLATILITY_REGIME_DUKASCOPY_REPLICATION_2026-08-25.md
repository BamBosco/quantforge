# XAUUSD Intraday Volatility Regime — Dukascopy Replication

## Decision

**The existing frozen Dukascopy XAUUSD dataset reproduces the offline
volatility-regime result.** This is a cross-venue historical replication for
the project closeout. It replaces neither the historical forward-confirmation
proposal nor the project's prohibition on execution.

## Reproducibility record

- Study: `xauusd_intraday_volatility_regime`, configuration version `0.1`.
- Runner: `tools/run_xauusd_volatility_regime.py`.
- Dataset: `dukascopy_demo_mt5_1_xauusd_m1_20230802_20260820_confirmation`.
- Raw file: `XAUUSD_M1_202308020104_202608202359.csv`.
- SHA-256 verified before loading:
  `1e4a9887251db3ad40cbb0a9e2ce49ab33332b737bb78242c36e7279dad383b6`.
- Source: Dukascopy Bank SA MT5 Demo / `Dukascopy-demo-mt5-1`.
- Timestamp treatment: recorded `Africa/Lagos` export timezone, normalized to
  UTC and then evaluated in `America/New_York`.
- Coverage: `2023-08-02T00:04:00Z` through `2026-08-20T22:59:00Z`.

## Result

| Measure | Result |
| --- | ---: |
| Valid complete New York weekday observations | 778 |
| Excluded sessions | 17 |
| Development scored sessions | 315 |
| Development MAE reduction | 16.87% |
| Holdout scored sessions | 156 |
| Holdout MAE reduction | 24.60% |
| Development windows meeting 5% reduction | 5 of 5 |
| Frozen offline-study gate | PASS |

The study uses only M1 close-to-close movement. It contains no orders, fills,
positions, P&L, execution-quality calculation, or trading authority.

## Scope

The raw Dukascopy export was already frozen in the repository for Candidate
003. Consequently, this result is a reproducible cross-venue replication, not
a claim that this data was newly acquired or untouched for this volatility
study. No additional seven-day export is required for this result.
