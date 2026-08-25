# Candidate 006 — Dukascopy MT5 XAUUSD Specification Evidence

## Status

**Provisional manual evidence only; not an accepted broker observation.**

Two user-supplied MT5 specification screenshots were reviewed on 2026-08-25.
The account/server identity was not visible in the images. The evidence is
therefore recorded as Dukascopy only by the user's stated broker scope; it
does not establish a connected account identity and cannot supply a risk,
sizing, or execution input.

No order was submitted, modified, or closed to obtain this record.

## Visible XAUUSD facts

| Field | Observed value |
| --- | --- |
| Digits | 3 |
| Contract size | 100 XAU |
| Spread | Floating |
| Stops level | 0 |
| Margin currency | XAU |
| Profit currency | USD |
| Calculation | Forex |
| Chart mode | By bid price |
| Trade permission | Full access |
| Execution | Market |
| GTC mode | Good till cancelled |
| Filling | Immediate or Cancel |
| Minimum volume | 0.01 |
| Maximum volume | 10,000 |
| Volume step | 0.01 |
| Volume limit | 1,000 |
| Weekday quote/trade sessions | 01:00–24:00 |
| Margin rate | 2.000000 initial and maintenance; approximately USD 9,288/lot displayed |

The screenshots also show floating spread and variable long/short swap values.
Those values are observations at capture time, not research parameters or
policy inputs.

## Deliberately unavailable

The screenshots do **not** establish the following required read-only
observation fields:

- Dukascopy account/server identity;
- current bid, ask, spread in points, and UTC observation time;
- latest completed XAUUSD M1 candle time;
- freeze level;
- tick size, tick value, tick-value loss, and tick-value profit;
- terminal connection state and source-event identifier.

Candidate 006 must continue to fail closed for sizing until a fresh read-only
MT5 observation supplies these facts and is linked through
`SQLiteXAUUSDBrokerProfileAudit`. This evidence must not be copied into the
Candidate 006 configuration, which intentionally contains no broker-contract
values.
