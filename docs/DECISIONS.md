# Architecture Decision Records

## ADR-001: Modular monolith

**Status:** accepted. **Decision:** use one deployable Python process with
strict package boundaries. **Rationale:** lower operational cost while the
platform is single-account and early stage. Revisit for independently scaling
or failure-isolated workloads.

## ADR-002: Risk-controlled event workflow

**Status:** accepted. **Decision:** strategy emits intents, risk emits approved
orders, execution accepts only approved orders. **Rationale:** makes bypassing
the risk gate structurally impossible within supported interfaces.

## ADR-003: Durable audit journal

**Status:** accepted. **Decision:** persist material inputs and decisions for
replay alongside the in-process dispatcher. **Rationale:** explainability and
incident reconstruction require more than transient pub/sub.
