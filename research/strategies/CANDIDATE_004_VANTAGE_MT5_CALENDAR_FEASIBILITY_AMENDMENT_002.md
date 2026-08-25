# Candidate 004 — Vantage MT5 Calendar-Feasibility Amendment 002

## Status

**Candidate identifier:** `candidate_004` (calendar feasibility only)
**Amends:** calendar-feasibility record and Amendment 001
**Status:** **PENDING — an August 2026 source offset is evidenced; full historical conversion policy is not yet frozen.**

## New direct XAUUSD timing evidence

On 24 August 2026, user-supplied evidence shows an actively updating standard
`XAUUSD` M1 chart. The terminal's current right-edge timestamp was approximately
13:30 while the Mac menu-bar clock was approximately 11:34. With the research
workstation configured for `Africa/Lagos` (UTC+1), this supports a Vantage MT5
server offset of **UTC+3** at that date.

This establishes an observed source-time offset for the current summer period.
It does not establish that the server uses UTC+3 throughout the proposed
archive, nor whether it shifts to UTC+2 in the opposite DST season.

## Calendar decision

The research calendar remains defined in `America/New_York`. No historical MT5
timestamp will be assigned to a New York date until Vantage's historical
server-time/DST convention is verified. No research ranges, eligible-date
population, or session counts are frozen or calculated.

## Required next evidence

Obtain Vantage's written statement for `VantageMarkets-Demo` covering:

1. server timezone;
2. winter and summer UTC offsets; and
3. DST-transition convention or dates.

That evidence will permit a formal source-time-to-`America/New_York` conversion
rule and a subsequent calendar-feasibility decision. No data rows were used,
and this amendment authorizes no export, analysis, strategy activity, replay,
or trading action.
