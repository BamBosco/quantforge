# Candidate 004 — Vantage MT5 Data-Source Intake Amendment 002

## Scope

**Candidate identifier:** `candidate_004` (data-source intake only)  
**Amends:** intake record and Amendment 001  
**Status:** **PENDING — terminal identity and native M1 interface evidenced; timestamp basis and research feasibility remain unresolved.**

This amendment relies only on user-supplied MT5 screen chrome, account labels,
dialog controls, and column headings. Visible market-data row values were not
read, transcribed, analyzed, or used. No CSV was exported or opened.

## Newly verified Vantage terminal facts

| Fact | Observed value | Status |
| --- | --- | --- |
| Broker/entity | Vantage Markets (Pty) Ltd | Verified from terminal title bar |
| MT5 server | `VantageMarkets-Demo` | Verified from terminal title bar / Accounts tree |
| Account environment | Demo Account — Hedge | Verified from terminal title bar |
| Selected standard instrument | `XAUUSD`, Gold US Dollar | Verified |
| `XAUUSD247` | Not selected; excluded from Candidate 004 scope | Verified scope control |
| Native history interface | Symbols → Bars | Verified |
| Timeframe | M1 | Verified |
| Displayed Bars interval | `2012.08.02 01:00` through `2026.08.21 00:00` | Verified as displayed terminal-interface bounds, not yet a UTC claim |
| Reported M1 quantity | 2,809,273 bars | Verified interface metadata only; no row-quality inference |
| Native export action | `Export Bars` button present | Verified; not used |
| Native Bars table headings | Date, Open, High, Low, Close, Tick Volume, Volume, Spread | Verified headings only; no row schema/content validation yet |

## Timestamp-basis constraint

The terminal displays a current terminal timestamp, but no explicit timezone or
UTC-offset label is visible. The server/export timezone therefore remains
`UNKNOWN`. The displayed Bars timestamps are terminal-formatted timestamps and
must not be labelled UTC, New York, or any fixed offset until the Vantage server
timestamp basis is independently evidenced. The Mac/menu-bar clock and displayed
session hours are not substitutes for that evidence.

## Remaining data-source blockers

1. Explicit Vantage server/export timezone or authoritative timestamp basis.
2. Confirmation that the displayed Bars interval is the terminal's actual
   retrievable archive boundary rather than only a requested/view range.
3. Frozen role-separated evaluation/confirmation range selection, based only on
   verified availability and chronology.
4. Export schema confirmation from a frozen raw export, after selection-record
   approval, without using data rows for performance.
5. Later structural-quality assessment of the evaluation export; no complete
   session count has been calculated.

## Non-authorization

This amendment authorizes no export, raw-row inspection, checksum calculation,
structural assessment, strategy creation, signal/performance analysis, replay,
confirmation access, paper/MT5/broker/live execution, optimization, or tuning.
