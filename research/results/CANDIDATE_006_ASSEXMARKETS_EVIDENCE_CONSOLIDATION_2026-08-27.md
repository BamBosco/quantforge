# Candidate 006 — AssexMarkets evidence consolidation

Date: 2026-08-27. This is an evidence assessment, not a production-execution
approval or a change to the provisional Candidate 006 Stage A policy.

## Evidence inventory

| Category | Evidence | Scope and conclusion |
| --- | --- | --- |
| Live read-only quotes | 473 accepted `:8766` receipts, 2026-08-26T13:30:08Z through 2026-08-27T03:49:33Z | Broker-scoped observations only. Live spreads were 24–37 raw points (P50 27, P95/P99 37). |
| Current clock | 194 EA 1.01 receipt-linked `time_provenance` objects | Current terminal server clock is UTC+3; terminal-local clock is UTC+1; terminal UTC matches receipt time. This does not establish winter/DST behavior or the CSV's timestamp basis. |
| Historical bars | Frozen native MT5 M1 CSV, 217,842 structurally valid rows, SHA-256 `45a24b5f53c5518f73a310800705ef0ce26036a8a315ee97c80073fb4bf85f33` | Source-clock quote/spread research only. P99.5 30 raw points, P99.9 50, maximum 358. No UTC conversion is made. |
| Demo execution | One manually submitted and closed 0.01-lot XAUUSD BUY | Genuine broker entry/exit and post-close flat-state corroboration. It is one observation, not a deviation distribution. |
| Broker website | Public MT5, metals, account, forex and terms pages | XAU/USD/MT5 availability; metals may use tiered margin; account-level volume/leverage terms; automated order-submitting EAs are prohibited. No authoritative XAUUSD server-time/DST/session/holiday schedule was found. |

## Timezone and historical normalization

UTC+3 is established for the observed 2026-08-26/27 MT5 server clock only.
The historical export spans 2026-01-02 through 2026-08-14, when a DST-changing
server could have a different winter offset. The broker's published GMT+0
statement applies to its forex page, not explicitly to XAUUSD metals or MT5
bar exports. Therefore the existing source-clock freeze remains authoritative;
creating a UTC-normalized historical manifest would introduce an unsupported
assumption and is not performed.

Required evidence before normalization:

1. Written broker confirmation that the XAUUSD MT5 server/export clock uses
   UTC+3 year-round, or its exact 2026 DST transition schedule; and
2. Confirmation that native MT5 XAUUSD Bars exports use that server clock.

## Policy reassessment

| Policy | Current conclusion | Disposition |
| --- | --- | --- |
| Spread | Historical P99.5 of 30 is useful central research evidence. The historical 358-point tail and live/demo 37-point spreads demonstrate that 30 cannot be an unconditional execution limit. Live coverage has not yet sampled rollover, news, or a broad distribution of stressed conditions. | Broker-specific research-supported, provisional. |
| Risk / maximum position | Live MT5 observations show 0.01 minimum/step, 100 maximum volume, contract size 100, USD margin/profit currencies, and a 20,000 USD demo equity snapshot. Broker pages say metal margin can be tiered. These facts do not provide an approved risk budget, stable margin schedule, or maximum-position mandate. | Provisional. |
| Session | MT5 screenshot/observations show the current source-clock trading session, and current server time is UTC+3. No authoritative XAUUSD DST, rollover, holiday, or export-clock statement is available. | Provisional. |
| Execution deviation | One authentic demo round trip captures entry/exit price and flat-state reconciliation; it lacks client request timestamp, quoted request price, terminal latency, MT5 retcode, rejected-order samples, and a distribution. Paper/replay fills remain labelled simulation evidence. | Partially evidenced, provisional. |

## Execution boundary

The AssexMarkets terms page says it prohibits automated bots, scripts and EAs
that submit orders without direct manual intervention. QuantForge remains
read-only/paper/simulation only: no broker-order submission was enabled or
attempted by this consolidation. Future production execution needs separate
written broker permission, owner authorization, and a reviewed architecture.

## Sources

- https://www.assexmarkets.com/metatrader5
- https://www.assexmarkets.com/metals
- https://www.assexmarkets.com/forex-cfd
- https://www.assexmarkets.com/standard
- https://www.assexmarkets.com/terms-and-conditions

