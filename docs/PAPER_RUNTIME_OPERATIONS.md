# Paper Runtime Operations

## Scope

`PaperRuntimeHost` operates only against validated read-only observations and
`PaperExecutor`. It has no MT5 order capability, live broker adapter, or
authority to activate a strategy.

## Cadence

- Deliver every accepted observation to `process()` immediately in event-time
  order.
- Run `heartbeat()` at a predeclared interval no longer than the runtime's
  maximum observation age and supply fresh executable quotes for every open
  instrument.
- A heartbeat processes protective exits, due scheduled exits, and both
  position and pending-order reconciliation. It never invents a fill if a
  usable quote is absent.
- The strategy is evaluated only from `process()`, never from a heartbeat.

## Fail-closed operation

The host accepts no new strategy entry when an observation is duplicate, stale,
future-dated, disconnected, degraded, incomplete, clock-regressed, lacks
instrument risk metadata, lacks an account snapshot, or fails reconciliation.

Position or pending-order drift blocks the runtime. Resolve the source of the
drift, reconstruct state, and call `recover()` only after reconciliation
matches. A manual kill switch blocks strategy evaluation and new entries while
the host continues lifecycle actions already due on the current observation.

## Restart and replay

1. Stop observation ingress; do not discard either SQLite database.
2. Preserve the append-only observation log and event journal with their
   checksums. Do not edit rows in place.
3. Create fresh portfolio, executor, pipeline, and host instances using the
   same frozen configuration and approved strategy version.
4. Replay the immutable observations in event-time order through `replay()`.
   The host evaluates each observation at its own original timestamp.
5. Compare reconstructed position and pending-order projections with the
   paper-state projection. Investigate any mismatch; do not call `recover()`
   until both match.
6. Resume ingress only after a fresh accepted observation passes the normal
   quality and reconciliation gates.

Replay requires deterministic strategy signal IDs and behavior. Replayed
journal events must retain the same causal order and checksums; a mismatch is a
fail-closed incident, not a reason to alter history.

## Retention

Keep the observation log, event journal, frozen strategy specification,
configuration, market metadata, event-calendar snapshot, and reconciliation
records together for the entire paper-validation period. Archive immutable
copies with checksums before any retention action. This project has no deletion
or compaction job; retention must not silently remove replay evidence.
