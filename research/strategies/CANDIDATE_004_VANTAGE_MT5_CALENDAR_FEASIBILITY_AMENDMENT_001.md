# Candidate 004 — Vantage MT5 Calendar-Feasibility Amendment 001

## Status

**Candidate identifier:** `candidate_004` (calendar feasibility only)  
**Amends:** `CANDIDATE_004_VANTAGE_MT5_CALENDAR_FEASIBILITY.md`  
**Status:** **PENDING.**

## New calendar-relevant evidence

The native Vantage MT5 Bars interface visibly offers `XAUUSD` M1 controls for
the displayed terminal-formatted interval `2012.08.02 01:00` through
`2026.08.21 00:00`, and reports 2,809,273 bars. This is sufficient evidence of
substantial apparent calendar span and native M1 interface availability, but it
is not evidence of UTC timestamps, complete research sessions, holiday
availability, or any future strategy window.

The terminal title establishes `VantageMarkets-Demo`, Demo Account — Hedge, and
Vantage Markets (Pty) Ltd. It does not display a timezone or UTC offset. The
broker/server timestamp basis remains `UNKNOWN`; New York conversion and DST
calendar assignment cannot yet be performed.

## Calendar decision

The displayed multi-year terminal span is potentially ample for a future older
evaluation period and later non-overlapping confirmation period. No ranges are
frozen and no session count is calculated because Candidate 004 has no approved
research window and no verified timestamp basis. All prior PENDING blockers
remain, especially server timezone, historical broker holiday/early-close
availability, and complete-window validation.

No market-data row was used for this amendment, and no export or confirmation
data access is authorized.
