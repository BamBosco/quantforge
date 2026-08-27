# Candidate 006 — AssexMarkets demo execution evidence

Date: 2026-08-26. Account: `AssexmarketsGlobal-Trade` demo. Instrument:
`XAUUSD`.

## Observed round trip

| Field | Value |
| --- | --- |
| Position ticket | `29455831` |
| Entry deal | `29196312` |
| Exit deal | `29196594` |
| Direction / volume | BUY / 0.01 |
| Entry server time | 2026-08-26 23:49:59 |
| Entry price | 4593.51 |
| Exit server time | 2026-08-26 23:53:43 |
| Exit price | 4592.61 |
| Realized profit | -0.90 USD |

The MT5 History screenshot is the source for the ticket, server-time, price,
volume, and realized-profit fields. The independent bridge receipts corroborate
the lifecycle:

- 20:50:04Z: position `29455831` and entry deal `29196312` observed
- 20:51:34Z: position marked -0.90 USD at current bid 4592.61
- 20:54:04Z: position absent and exit deal `29196594` at 4592.61 for -0.90 USD
- 20:55:34Z: account flat with zero margin and balance/equity 19,999.10 USD

## Execution observations

The bridge captured the XAUUSD spread at 37 points throughout the open-position
interval, compared with 24–29 points immediately before entry. The observed
entry price equals the contemporaneous ask, and the exit price equals the
contemporaneous bid. This is consistent with a market BUY round trip and
demonstrates that the broker's spread can exceed the historical P99.5 research
value of 30 points.

This is one demo observation, not a promoted execution policy. The evidence
does not contain the client-side request timestamp, MT5 retcode, terminal
latency, or a distribution of fills under multiple conditions.
