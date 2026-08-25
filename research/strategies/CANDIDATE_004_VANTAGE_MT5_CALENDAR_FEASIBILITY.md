# Candidate 004 — Vantage MT5 Calendar-Feasibility Record

## Scope and status

**Candidate identifier:** `candidate_004` (calendar/data-source feasibility only)  
**Research timezone:** `America/New_York`  
**Status:** **PENDING — calendar feasibility not established.**

This record is independent of the terminal's displayed trading sessions. It
does not inspect market-data rows, calculate signals or performance, choose a
strategy, freeze a data range, authorize export, or authorize confirmation
access, replay, paper, broker, or live execution.

## Proposed research-calendar definition

An eligible candidate date is a Monday–Friday local civil date in
`America/New_York` for which the eventual frozen Vantage M1 export contains a
complete required research window. Calendar weekday membership alone is not
evidence of a complete session.

The eventual strategy-specific required window is currently `UNKNOWN` because
no Candidate 004 trading specification exists. Any future selection record must
state that window explicitly and require all of its M1 timestamps to be present
after broker-to-New-York conversion. Missing, duplicate, malformed, spreadless,
stale, clock-regressed, or session-closed minutes cannot be filled or inferred.

## Timezone and DST rule

All later source timestamps must be converted from a verified Vantage
server/export timezone to UTC, then converted with the IANA
`America/New_York` timezone database. A fixed UTC offset is prohibited:

- New York standard time uses UTC−05:00.
- New York daylight time uses UTC−04:00.
- DST transitions must be resolved by timezone-aware conversion for every
  timestamp across the frozen period, including ambiguous/nonexistent local
  times. No hard-coded annual offset or terminal/Mac-clock assumption is valid.

The Vantage server/export timezone is currently `UNKNOWN`; therefore no broker
timestamp can yet be deterministically assigned to a New York research date.

## Observed broker-session constraints

The user-supplied MT5 `XAUUSD` Specification displays these recurring terminal
sessions:

| Terminal weekday | Quotes | Trade |
| --- | --- | --- |
| Monday–Thursday | 01:00–23:58 | 01:01–23:58 |
| Friday | 01:00–23:57 | 01:01–23:57 |
| Saturday/Sunday | none displayed | none displayed |

These are terminal-session metadata, not a research calendar. Because the
terminal/server timezone is unknown, the intervals cannot be mapped to
`America/New_York`, and cannot yet prove that a future required intraday window
is fully quoted or tradable. The displayed one-minute trading delay and
end-of-day/week gaps are explicit constraints for future window-completeness
checks.

## Holiday and early-close treatment

US federal holidays, US exchange holidays, and early-close calendars are not
substitutes for Vantage's XAUUSD CFD quoting calendar. The relevant controlling
evidence is Vantage's historical XAUUSD quote/trade availability in the frozen
export plus any terminal-displayed Vantage session/holiday metadata.

Until that metadata is verified, every weekday that may include a Vantage
closure, shortened session, maintenance interval, holiday schedule, or other
broker interruption is an unresolved calendar-risk date. A later structural
quality assessment must exclude any date whose full strategy-required window is
not present; it must not infer a bar or treat a US calendar label as proof of
availability.

## Expected eligible-date population

No historical M1 archive start/end boundary has been observed. Therefore the
calendar weekday count, number of potentially eligible dates, number of
complete sessions, and capacity for the future protocol are all **UNKNOWN**.

Before freezing evaluation and confirmation ranges, the native MT5 M1 Bars
export dialog must provide the exact earliest and latest Vantage `XAUUSD` M1
boundaries. Only then may a pre-inspection selection record calculate calendar
weekday capacity for an older evaluation interval and a later non-overlapping
confirmation interval. The >=709 complete-session and future protocol capacity
gates require later structural assessment; calendar counts alone never pass
them.

## Calendar conflicts and required resolution

| Conflict | Status | Required resolution |
| --- | --- | --- |
| Server/export timezone unknown | Blocking | Record terminal/server timezone or authoritative export timestamp basis. |
| M1 history boundaries unknown | Blocking | Observe native Bars export-dialog boundaries without opening rows. |
| Broker historical holiday/early-close calendar unknown | Blocking | Preserve terminal/broker metadata and later validate complete windows from frozen export. |
| Research-required intraday window unknown | Blocking | Define only in a separately approved Candidate 004 specification. |
| Calendar capacity for future protocol unknown | Blocking | Calculate from observed export boundaries, then independently structurally assess. |

## Decision

**PENDING.** The research timezone/DST method and observed recurring terminal
session constraints are documented, but Vantage calendar feasibility cannot pass
until the server timestamp basis, M1 archive boundaries, broker holiday/early
close evidence, future required window, and complete-session capacity are
verified without using market behavior.
