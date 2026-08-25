# Candidate 006 — Dukascopy MT5 XAUUSD Specification Evidence

## Status

**Manual screenshot evidence only; not an accepted broker observation.**

Five user-supplied MT5 screenshots were reviewed on 2026-08-25. They identify
the connected demo server as `Dukascopy-demo-mt5-1`. The visible account
number is deliberately not recorded. This evidence establishes the broker
venue for Candidate 006, but cannot supply a risk, sizing, or execution input
because it lacks the required read-only bridge receipt and fresh M1 snapshot.

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
| Margin rate | 2.000000 initial and maintenance; approximately USD 9,284–9,288/lot displayed |

The screenshots show a floating spread and variable long/short swap values.
A later screenshot establishes an `XAUUSD,M1` chart. It visibly reports one
closed-bar record as `2026.08.25 18:12`, open 4633.205, high 4635.245, low
4633.205, close 4634.195, and tick volume 225. The chart's visible price label
is 4645.335. These values are observations at capture time, not research
parameters or policy inputs. The screenshot does not show an ask quote or an
unambiguous UTC/server timestamp for a fresh bridge receipt.

## Deliberately unavailable

The screenshots do **not** establish the following required read-only
observation fields:

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
