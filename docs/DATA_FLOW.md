# Data Flow

1. A data adapter receives a vendor observation and assigns source metadata.
2. Validation checks schema, timestamps, ordering, duplicates, gaps, and
   instrument identity. Rejected records are retained with a reason.
3. Validated observations are durably recorded and emitted as domain events.
4. Strategies consume only validated, point-in-time observations and emit
   trade intents.
5. Risk produces a decision; only approvals enter execution.
6. Execution outcomes update the portfolio and durable journal.
7. Analytics and dashboards consume journaled facts, never mutable strategy state.

Event time, receive time, source, dataset version, and transformation version
must be retained so research can be reproduced without look-ahead bias.
