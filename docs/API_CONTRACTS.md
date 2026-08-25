# API Contracts

## Contract rules

Domain events are immutable, versioned records with a unique `event_id`, an
UTC `occurred_at`, a correlation identifier, a causation identifier where
applicable, a schema version, and a payload. Consumers must be idempotent.
Unknown event versions are rejected and journaled rather than guessed.

## Core workflow events

| Event | Producer | Permitted consumer | Purpose |
|---|---|---|---|
| `MarketDataReceived` | market data | strategies, journal | Validated market observation |
| `TradeIntentGenerated` | strategy | risk only | Unsized proposal with entry and stop |
| `RiskDecisionRecorded` | risk | journal, analytics | Approved or rejected decision and reasons |
| `EventRiskDecisionRecorded` | risk | journal, analytics | Calendar snapshot, blackout decision, and any cancel/flatten action |
| `OrderApproved` | risk | execution only | Sized, approved, expiring order |
| `ExecutionOutcomeRecorded` | execution | portfolio, journal | Accepted, filled, canceled, or failed outcome |
| `KillSwitchTriggered` | risk | execution, strategies, journal | Halt and flatten request |

## Invariants

- An intent has no executable quantity.
- An approved order identifies the approving decision and policy version.
- Execution rejects non-approved orders and expired approvals.
- All state-changing events are journaled before or atomically with handling.

## Adapter ports

Ports are interfaces owned by QuantForge. Broker, data-vendor, database, and
notification SDKs remain behind their implementations. Adapters must not leak
vendor-specific types into domain contracts.
