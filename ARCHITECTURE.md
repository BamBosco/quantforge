# Architecture

## Decision record

QuantForge uses a **single-process modular monolith**. It avoids premature
distributed operations while retaining boundaries that can be extracted later.
The platform uses a typed in-process event dispatcher for workflow and a
durable journal for audit and replay. The dispatcher is not a source of truth.

## Dependency direction

```text
domain <- application <- infrastructure
                 ^
                 └── module packages (risk, strategy, portfolio, execution)
```

The domain package contains value objects and event contracts; it has no
vendor, database, or framework dependency. Infrastructure implements ports
defined by the application/domain layers.

## Mandatory order path

`MarketDataReceived -> TradeIntentGenerated -> RiskDecision -> ApprovedOrder -> ExecutionOutcome`

`TradeIntentGenerated` is not executable. Only a valid `ApprovedOrder` issued
by the Risk Engine may enter an execution adapter. A kill-switch signal stops
new approvals and requests controlled flattening through the execution port.

## Boundaries

| Package | Responsibility | Must not depend on |
|---|---|---|
| `market_data` | Ingest, normalize, validate, persist data | strategy or execution vendors |
| `strategies` | Produce trade intents | risk sizing or execution |
| `risk` | Size, approve/reject, halt | broker SDKs |
| `execution` | Execute approved orders and reconcile | strategy implementations |
| `portfolio` | Positions, cash, P&L, exposure | strategy implementations |
| `backtest` | Deterministic simulation | production adapters |
| `journal` | Durable audit record and replay | strategy internals |

## Deferred decisions

- External message broker: revisit only for independently scaled workloads.
- PostgreSQL/TimescaleDB: revisit when SQLite write concurrency or market-data
  volume requires it.
- Compliance rule packs: define only after relevant jurisdictions/accounts are known.

See [API contracts](docs/API_CONTRACTS.md) and [decision records](docs/DECISIONS.md).
