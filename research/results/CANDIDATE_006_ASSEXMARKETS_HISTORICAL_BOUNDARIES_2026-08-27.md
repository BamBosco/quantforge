# Candidate 006 — historical XAUUSD boundaries

This report analyzes the frozen native MT5 M1 export without changing it.
Source-clock times are reported as exported; no UTC conversion is assumed.

## Results

- 1,191 source dates were observed across 2022–2026.
- 1,173 dates (98.5%) begin at 01:00; 17 begin at 00:00 and one at 02:01.
- The normal daily span is approximately 01:00–23:54/23:58, implying a
  recurring approximately one-hour daily maintenance gap.
- 1,197 gaps exceed 30 minutes. This includes 949 inter-day/daily gaps and
  248 Friday-to-Monday or other weekend-like gaps. These are historical
  absence patterns, not broker-authoritative trading hours.
- Eighteen delayed/shifted source dates were identified. Thirteen are isolated
  2024–2025 Friday delayed opens between 00:01 and 00:19, one is a 2022
  02:01 open, and five are the exact 2025-10-27 through 2025-10-31
  00:00–22:58 anomaly.
- Delayed opens often have elevated first-bar spreads (for example 54–176
  points on the 2024–2025 Friday cases), while the October 2025 anomaly has
  six-point first/last spreads. This supports a distinction between
  low-liquidity/restart events and the separate five-session clock anomaly.

## Evidence classification

- **Historically observed:** source-date first/last bars, recurring daily gaps,
  weekend-like gaps, delayed opens, and boundary spreads.
- **Statistically inferred:** a normal source-clock daily maintenance interval
  and predominantly UTC+3 structural alignment.
- **Unresolved:** whether any gap is a broker session closure, holiday, early
  close, terminal/data outage, or export artifact; the historical timezone/DST
  rule; and the broker-authoritative XAUUSD rollover schedule.

The reproducible machine-readable output is
`research/results/live_boundary_analysis/xauusd_historical_boundaries_2026-08-27.json`.
Live EURUSD/XAUUSD receipts currently corroborate UTC+3 only for the observed
August 2026 MT5 server state. They do not convert these historical boundaries
to UTC or promote the Candidate 006 session policy.
