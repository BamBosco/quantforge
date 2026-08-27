# Candidate 006 — AssexMarkets XAUUSD authority assessment

Date: 2026-08-26. This assessment does not authorize live trading or alter the
provisional Candidate 006 profile.

## A. Broker-published facts

The broker's MT5 page lists XAUUSD as an available metal CFD. Its metals page
says margin can be tiered by position size, but does not publish an XAUUSD
contract sheet, hours, rollover, holidays, or DST rule. Its forex-hours page
says its listed forex times are server time GMT+0, but does not state that this
applies to metals or to this historical export. It therefore cannot establish
the XAUUSD server/export timezone.

Account pages advertise 0.01/100 minimum/maximum lots and account-level
leverage/hedged-margin terms. These are product descriptions, not a substitute
for symbol-specific MT5 terms or actual margin charged to this demo account.

Sources consulted: https://www.assexmarkets.com/metatrader5,
https://www.assexmarkets.com/metals, https://www.assexmarkets.com/forex-cfd,
https://www.assexmarkets.com/standard, and
https://www.assexmarkets.com/leverage-plus.

## B. Live MT5-observed facts

Fresh accepted receipts from `AssexmarketsGlobal-Trade` identify the connected
broker scope. The 2026-08-26T19:21:40Z receipt reported XAUUSD point/digits
0.01/2; contract size 100; tick size and profit/loss tick values 0.01/1.0;
USD profit and margin currencies; volume minimum/step/maximum 0.01/0.01/100;
FOK, IOC, and BOC filling modes; stop/freeze levels 0/0; calculation, trade,
and order modes 2/4/127; and account equity 20,000 USD with no current margin.

These are receipt-linked observations, not enduring broker promises. The
previous EA receipts did not retain raw MT5 server-clock time, so they cannot
retrospectively establish a server offset. EA 1.01 adds append-only
`time_provenance` for future receipts; it must be compiled and reattached.

## C. Historical CSV-derived facts

The frozen M1 export has 217,842 structurally valid bars from source-clock
2026-01-02 01:00 through 2026-08-14 11:59. Its raw spread field has P99.5 30
points and maximum 358. This supports broker-specific historical quote-spread
research only. It does not establish timezone, trading hours, fills, latency,
rejections, or execution deviation.

## D. Assumptions and inferences

None are promoted as facts. In particular, do not infer that the historical
CSV uses GMT+0, that GMT+0 applies to XAUUSD, or that the public forex rollover
at 21:00 GMT+0 applies to XAUUSD.

## Policy disposition

| Policy | Disposition | Remaining requirement |
| --- | --- | --- |
| Spread | Research-supported, still provisional | Historical P99.5 30, max 358; require live normal, stressed, rollover and scheduled-news coverage plus owner approval. |
| Risk / maximum position | Provisional | Observed symbol constraints do not supply a strategy risk budget, actual margin behavior, or owner mandate. |
| Session | Provisional | No authoritative XAUUSD timezone, DST, hours, rollover, or holiday record. |
| Execution deviation | Partially evidenced, still provisional | One manual 0.01-lot demo round trip completed at 4593.51 -> 4592.61 for -$0.90; bridge corroborated entry/exit and observed 37-point spread; request price, latency, retcode, and distributional evidence remain unavailable. |

No AssexMarkets policy is production-approved. The Dukascopy 760-point cap
remains scoped to its own provisional research profile.

## Required external evidence

1. Broker support or contract documentation binding XAUUSD MT5 server time,
   DST, hours, rollover, and holidays to `AssexmarketsGlobal-Trade`.
2. A fresh EA 1.01 receipt, repeated around a DST boundary, to measure the
   terminal server-to-UTC offset. This does not itself prove the historical
   export clock.
3. Receipt-linked live quote coverage across stated stressed conditions.
4. Additional broker-authorized demo request/fill/rejection evidence before any
   review of execution deviation. The first manual demo round trip is recorded
   but is insufficient to establish a policy.
