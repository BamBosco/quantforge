# Candidate 004 — Vantage MT5 Data-Source Intake Amendment 003

## Scope and status

**Candidate identifier:** `candidate_004` (data-source intake only)
**Amends:** intake record and Amendments 001–002
**Status:** **PENDING — live XAUUSD source-time offset observed; historical DST rule remains unverified.**

No export, raw-row inspection, strategy work, replay, confirmation-data access,
or trading-related action occurred for this amendment.

## Live XAUUSD timestamp observation

User-supplied MT5 evidence dated 24 August 2026 shows the standard `XAUUSD` M1
chart actively updating. At the captured Mac local time of approximately 11:34,
the rightmost live chart timestamp was approximately 13:30 on the same date.
This is an observed Vantage-terminal-to-computer-clock difference of
approximately **+2 hours**.

The research workstation is configured as `Africa/Lagos` (UTC+1). Subject to
the Mac clock being accurate, the observed Vantage MT5 server offset on this
date is therefore **UTC+3**. This is direct XAUUSD live-time evidence, rather
than an inference from quoted session hours or a BTC-only observation.

## Constraint retained

One summer-time offset observation does not establish the server's historical
DST rule, its winter offset, or the timestamp basis of every archived bar.
The source-time conversion remains provisional until Vantage confirms the
timezone/DST convention in writing, or a second controlled observation covers
the opposite DST season.

## Remaining blockers

1. Written Vantage confirmation of the `VantageMarkets-Demo` server timezone,
   winter/summer UTC offsets, and DST transition convention.
2. Confirmation that the Bars-interface dates are actual retrievable native
   archive boundaries, not merely request controls.
3. Authorization and freezing of a role-separated export plan; no export is
   authorized by this amendment.

## Non-authorization

This amendment authorizes no CSV export, market-data row inspection,
calculation, strategy creation, replay, backtest, optimization, tuning,
confirmation inspection, paper/MT5/broker/live execution, or order activity.
