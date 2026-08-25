# Candidate 004 — Vantage MT5 Data-Source Intake Amendment 001

## Scope and evidence status

**Candidate identifier:** `candidate_004` (data-source intake only)  
**Amends:** `CANDIDATE_004_VANTAGE_MT5_DATA_SOURCE_INTAKE.md`  
**Status:** Terminal symbol-specification evidence added; source decision remains
**PENDING**.

This amendment records only fields visibly shown in the user-supplied MT5
Symbol Specification screenshots. It does not create a Candidate 004 strategy,
authorize export or raw-row inspection, establish M1 depth, or authorize replay,
optimization, paper/live execution, or confirmation access.

## Verified terminal observations

| Fact | Observed value | Status |
| --- | --- | --- |
| Exact selected symbol | `XAUUSD` | Verified |
| Description | Gold US Dollar | Verified |
| `XAUUSD247` selected | No | Standard `XAUUSD` is shown; `XAUUSD247` remains excluded. |
| Exchange | `XCCY` | Verified |
| Sector / industry | Commodities / Precious Metals | Verified |
| Digits | 2 | Verified |
| Contract size | 100 | Verified |
| Spread | Floating | Verified |
| Stops level | 20 | Verified |
| Margin currency | USD | Verified |
| Profit currency | USD | Verified |
| Calculation | CFD Leverage | Verified |
| Tick size | Displayed as `0.00` | Verified display value; usable tick increment remains UNKNOWN. |
| Tick value | Displayed as `0` | Verified display value. |
| Chart mode | By bid price | Verified |
| Trade permission | Full access | Verified terminal setting; no trade action is authorized. |
| Execution | Market | Verified |
| Filling | Immediate or Cancel | Verified |
| Expiration | GTC, Today, Specified | Verified |
| Orders | All | Verified |
| Minimum volume | 0.01 | Verified |
| Maximum volume | 100 | Verified |
| Volume step | 0.01 | Verified |
| Swap type | In points | Verified |
| Swap long / short | -83.45 / 31.8 | Verified display values; irrelevant to any future intraday specification unless explicitly selected. |
| Quotes/trade sessions, Mon–Thu | 01:00–23:58 / 01:01–23:58 | Verified terminal display |
| Quotes/trade session, Fri | 01:00–23:57 / 01:01–23:57 | Verified terminal display |
| Saturday/Sunday sessions | None displayed | Verified terminal display |

## Still unknown

The screenshots do not establish the broker/legal entity, MT5 server name,
account number or demo/live status, point size, usable tick increment, account
currency, bid/ask export fields, recorded-spread field, M1 availability,
earliest/latest M1 history boundary, export timestamp basis, or MT5 server
timezone. Those fields remain `UNKNOWN` and must not be inferred from the
symbol name, digit count, displayed tick rounding, the user-provided broker
label, another venue, or public web material.

## Decision

**PENDING.** Standard `XAUUSD` symbol identity, selected specification fields,
and quoted/trading-session display are now evidenced. The source cannot pass
research-data feasibility until the server/account provenance, usable point/tick
definition, M1 archive boundary, export schema, bid/ask/spread sufficiency, and
timestamp-timezone provenance are observed without inspecting raw market rows.
