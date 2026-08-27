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

## Direct HFM MT5 evidence supplied on 2026-08-27

The attached HFM client-portal and MT5 Specification screenshots are direct
observations of one HFM demo account. They are not a substitute for current
terms or a machine-readable receipt, and the account identifier is intentionally
not reproduced here.

### Account and server

- Account type: **Demo Premium**
- Platform: **MT5**
- Displayed leverage: **1:1000**
- Displayed free margin: **100,000 USD**
- Server: **HFMMarketsGlobal-Demo**
- Legal entity shown in the portal: **HF Markets (SV) Ltd**

### XAUUSD Specification

- Symbol: `XAUUSD`, Gold vs US Dollar
- Digits: **2**
- Contract size: **100**
- Spread: floating
- Stop level: **0**
- Margin currency: **USD**
- Profit currency: **USD**
- Calculation: **CFD Leverage**
- Tick size: **0.01**
- Tick value: **0.1**
- Hedged margin: calculate using larger leg
- Trade access: Full access
- Execution: Instant
- Filling: Fill or Kill, Immediate or Cancel
- Expiration: All; orders: All
- Volume: **0.01 minimum, 0.01 step, 100 maximum**
- Swap type: points; long **-12.6**, short **-4.6**
- Displayed swap multipliers: Monday 1, Tuesday 1, Wednesday 3,
  Thursday 1, Friday 1
- Displayed quote/trade sessions: Monday–Friday `00:00–24:00`; Sunday and
  Saturday were not shown as active sessions.

### EURUSD Specification

- Symbol: `EURUSD`, Euro vs US Dollar
- Digits: **5**
- Contract size: **100,000 EUR**
- Spread: floating
- Stop level: **0**
- Margin currency: **EUR**
- Profit currency: **USD**
- Calculation: **Forex**
- Hedged margin: **100,000** (as displayed)
- Trade access: Full access
- Execution: Instant
- Filling: Fill or Kill, Immediate or Cancel
- Expiration: All; orders: All
- Volume: **0.01 minimum, 0.01 step, 500 maximum**
- Swap type: points; long **-0.7**, short **-1**
- Displayed swap multipliers: Monday 1, Tuesday 1, Wednesday 3,
  Thursday 1, Friday 1
- Displayed quote/trade sessions: Monday–Friday `00:00–24:00`; Sunday and
  Saturday were not shown as active sessions.
- Displayed floating notional margin-rate tiers: `0–300,000` at 1.0,
  `300,000–500,000` at 2.0, and `500,000–10,000,000,000` at 3.0 for both
  market buy and market sell.

### Evidence classification and limitations

These fields are **directly observed from the HFM MT5 terminal UI** for this
account/server and should be verified with authenticated read-only receipts.
They materially reduce uncertainty about the demo server, account type,
symbols, contract sizes, volume bounds, currencies, and displayed margin-rate
structure. They do not establish:

- the exact XAUUSD daily break, rollover timestamp, Friday close, Sunday open,
  or holiday/early-close calendar;
- whether the displayed account leverage applies uniformly across XAUUSD
  notional tiers;
- stop-out, liquidation, news, latency, scalping, VPS, copying, or other
  execution restrictions;
- HFM's legal permission for the QuantForge Expert Advisor;
- historical MT5 export timezone/DST behavior.

The apparent `00:00–24:00` weekday sessions should be treated as a broad
symbol-session display, not proof that quotes and executable trading are
continuous through every minute or that weekends are open.
