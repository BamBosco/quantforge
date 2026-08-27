# HFM broker evidence and isolated collection design

Date: 2026-08-27

## Scope and safety boundary

This is research only. No HFM connection, order submission, account login, or
Candidate 006 policy change was performed. Existing AssexMarkets collectors,
databases, historical data, and Candidate 006 architecture are unchanged.

## Evidence available from HFM sources

| Requirement | Finding | Classification |
| --- | --- | --- |
| MT5 availability | HFM's Forex and Metals pages list MT5 among the available platforms. | Broker-authoritative, asset-class level |
| Supported account types | The public account page is region-dependent and did not expose a reliable current account-type/MT5 matrix. | Unresolved |
| MT5 demo server name | No authoritative public page identified the current demo server string. | Unresolved |
| EURUSD/XAUUSD | Forex and Metals are advertised, but the public pages do not explicitly guarantee the exact symbols, suffixes, or visibility for every account. | Asset class authoritative; symbols unresolved |
| Regular Forex schedule | Monday 00:00 through Friday 23:59, server time. | Broker-authoritative, Forex only |
| Server clock | Winter GMT+2; summer GMT+3. | Broker-authoritative, current published rule |
| DST | Begins last Sunday of March and ends last Sunday of October. | Broker-authoritative, current published rule |
| Sunday reopen | HFM describes a pre-open rate-refresh period and weekend-held orders executing at the next available price, but gives no precise executable Sunday timestamp. | Broker-authoritative restriction; timestamp unresolved |
| Friday close | No separate precise Friday close time was published on the reviewed trading-hours page. | Unresolved |
| Daily XAUUSD break/rollover | No XAUUSD-specific break or rollover timestamp was published. | Unresolved |
| Holiday/early-close schedule | No current authoritative holiday timetable was located. | Unresolved |
| Weekend execution | Pre-open quotes are not executable for new market orders; after opening, trades may be placed. Weekend-held orders can execute at the next available price, with thinner liquidity and wider spreads possible. | Broker-authoritative |
| Contract specification | Public pages did not provide contract size, volume min/step/max, digits, tick values, margin currency, stop/freeze levels, or symbol suffixes. | Unresolved |
| Margin/leverage | HFM states metals can be traded with leverage and provides risk disclosures, but no dependable numeric symbol/account margin schedule was exposed. | General statement authoritative; numbers unresolved |
| Expert Advisors | No reviewed authoritative HFM page established a general EA permission or prohibition. | Unresolved |
| Automated-trading restrictions | Client agreement and terms must be checked for latency arbitrage, excessive-order activity, copying, VPS, news trading, scalping, and abusive-feed restrictions. | Unresolved |

Authoritative sources reviewed:

- [HFM Forex](https://www.hfm.com/int/en-ng/trading-instruments/forex)
- [HFM Metals](https://www.hfm.com/int/en-ng/trading-instruments/metals)
- [HFM Markets](https://www.hfm.com/int/en-ng/trading-instruments)
- [HFM Trading Hours](https://www.hfm.com/int/en-ng/trading-instruments/trading-hours)
- [HFM Client Agreement](https://www.hfm.com/getTerms?lang=en-ng&branch=HFSV&type=client_agreement)
- [HFM Risk Disclosure](https://www.hfm.com/getTerms?lang=en-ng&branch=HFSV&type=risks_disclosures)

The applicable HFM legal entity and jurisdiction must be identified before
treating account, leverage, or automated-trading terms as applicable.

## What must be collected from the HFM MT5 terminal

Create the HFM demo account first, then record the exact account/server identity
and capture fresh read-only receipts for both symbols. The terminal must provide:

1. Exact MT5 server string, login, account type, currency, leverage, stop-out,
   and demo expiry/inactivity terms.
2. Market Watch visibility and exact broker symbols for EURUSD and XAUUSD.
3. **Specification** values for each symbol: contract size, digits, point,
   tick size/value, volume min/step/max, trade and order modes, filling modes,
   margin/profit currencies, stop/freeze levels, and swap fields.
4. Repeated time-provenance receipts across ordinary periods and the weekly
   boundary to validate the published GMT+2/GMT+3 seasonal clock.
5. XAUUSD and EURUSD observations around the daily break, rollover, Friday
   close, and Sunday/Monday reopen.
6. Current HFM holiday or early-close notices from the client portal or trading
   desk, matched to observed receipts.

Terminal observations are direct MT5 evidence, not substitutes for terms that
only HFM can authorize.

## Reuse of QuantForge bridge

The existing `QuantForgeReadOnlyBridge` can be reused unchanged. It accepts
authenticated versioned snapshots, records broker/server identity and raw time
provenance, persists payload digests, and has no order-submission endpoint. The
EA is already parameterized by one symbol and one destination; no HFM-specific
code is needed for a first collection.

Use the same compiled read-only EA only after confirming that HFM's applicable
terms permit the intended observation EA. Keep all automated execution disabled.

## Proposed isolated HFM path

Use a new loopback receiver and database, never an AssexMarkets path:

| Scope | Proposed value |
| --- | --- |
| Receiver | `127.0.0.1:8768` |
| Database | `data/hfm/mt5_observations.sqlite3` |
| Expected symbol | Set per receiver: `EURUSD` or `XAUUSD` |
| EURUSD optional database | `data/hfm_eurusd/mt5_observations.sqlite3` |
| XAUUSD optional database | `data/hfm_xauusd/mt5_observations.sqlite3` |
| Candidate 006 audit | Not attached |
| Execution | Disabled |

For strongest isolation, run two HFM receivers (for example `:8768` EURUSD
and `:8769` XAUUSD) with separate databases and `--expected-symbol` guards.
Attach two charts/EA instances in the HFM MT5 terminal. This matches the
existing single-symbol/single-endpoint design and avoids symbol or endpoint
transitions. Do not reuse `:8766`, `:8767`, or either AssexMarkets database.

## Exact next MT5 action

Open an HFM demo account in the applicable jurisdiction and send the exact
server name/login environment (not the password). In MT5, open Market Watch
and verify that `EURUSD` and `XAUUSD` are visible; open **Specification** for
each and provide screenshots or a transcription of the fields above. Do not
attach the EA or enable automated trading until the HFM legal entity and EA
terms have been checked. Once that information is available, the isolated
`:8768`/`:8769` read-only path can be activated without touching AssexMarkets.

## Conflicts and non-conclusions

HFM's published Forex schedule and seasonal server clock do not establish
XAUUSD-specific hours, rollover, holidays, margin tiers, or historical export
timezone. A future MT5 receipt that differs from the published schedule must
be preserved as a conflict for verification, not silently normalized or used to
alter Candidate 006.
