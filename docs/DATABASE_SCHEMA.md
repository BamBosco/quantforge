# Database Schema

SQLite is the Version 0.1 local durable store. Database access is isolated in
infrastructure repositories so migration remains feasible.

## Required logical records

| Record | Minimum fields |
|---|---|
| `event_journal` | id, type, schema version, occurred-at, correlation id, payload, checksum |
| `market_observation` | instrument, event time, receive time, source, dataset version, values, quality status |
| `risk_decision` | decision id, intent id, policy version, result, reasons, sizing inputs |
| `order` | approved order id, decision id, lifecycle status, idempotency key |
| `fill` | broker fill id, order id, timestamps, quantity, price, fees |
| `position_snapshot` | account, instrument, timestamp, quantity, cost, realized/unrealized P&L |
| `research_run` | hypothesis id, code revision, dataset version, configuration, seed, results |

Use UTC ISO-8601 timestamps, decimal-safe numeric representation, foreign keys,
and immutable append-only journal records. Raw data storage and large tick data
are excluded from the SQLite transactional database; retain them in a governed
dataset store with manifests.
