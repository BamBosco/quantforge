# MT5 Integration

## Safety boundary

MetaTrader 5 is an infrastructure adapter, never a dependency of domain,
strategy, or risk code. The mandatory order path remains:

`MarketDataReceived -> TradeIntentGenerated -> RiskDecision -> ApprovedOrder -> ExecutionOutcome`

The first MT5 demo phase is **read-only connectivity**. It can receive an
account, XAUUSD quote, symbol specification, completed M1 candle, current
position/order observations, and recent deal observations from the terminal.
It cannot send, modify, or close an order. Its local service has no order
endpoint. This proves data mapping and the safety boundary; it does not prove
that any strategy is profitable.

The Headway Demo XAUUSD specification is recorded in
[`config/brokers/headway_demo.toml`](../config/brokers/headway_demo.toml).
Future execution code must query and compare this live specification at startup,
and refuse execution when a material contract field differs.

## Phase 1: connect the demo terminal safely

The source file to compile is
[`mt5/experts/QuantForgeReadOnlyBridge.mq5`](../mt5/experts/QuantForgeReadOnlyBridge.mq5).
It contains no MT5 trade operation such as `OrderSend` or `PositionClose`.

1. In a macOS Terminal, choose a private random bridge token. Keep it off chat,
   screenshots, Git, and this repository. Set it only in the terminal session
   where the local bridge will run:

   ```zsh
   export QUANTFORGE_MT5_BRIDGE_TOKEN='choose-a-long-private-random-value'
   ```

2. From the QuantForge project folder, start the loopback-only receiver:

   ```zsh
   PYTHONPATH=src python3 -m quantforge.infrastructure.mt5.read_only_bridge \
     --observation-log data/paper_mode/mt5_observations.sqlite3
   ```

   It should say it is listening on `http://127.0.0.1:8765`. Leave that terminal
   window open. This service accepts snapshots only from the same computer.

3. In MT5, open **Tools -> Options -> Expert Advisors**. Enable *Allow WebRequest
   for listed URL*, then add exactly:

   ```text
   http://127.0.0.1:8765
   ```

4. Open **Tools -> MetaQuotes Language Editor**. Copy the EA source above into
   `MQL5/Experts/QuantForgeReadOnlyBridge.mq5`, compile it, and attach it to the
   `XAUUSD` M1 chart on the already selected Headway demo account. In its Inputs,
   enter the same private token and leave the default URL and 30-second heartbeat.

5. Verify it without trading:

   ```zsh
   curl http://127.0.0.1:8765/healthz
   curl -H "Authorization: Bearer $QUANTFORGE_MT5_BRIDGE_TOKEN" http://127.0.0.1:8765/v1/mt5/latest
   ```

   The second command should show the demo server, XAUUSD bid/ask, contract
   limits, and position count. A result of `404 no snapshot received` means the
   EA has not connected yet; it does **not** create a trade.

## Future phases

1. Reconcile snapshots against the configured broker contract and Risk Engine.
2. Run signal and risk decisions in dry-run mode: log what would be approved or
   rejected, with no broker command.
3. Run a tightly scoped demo canary only after an independently validated
   strategy exists, with explicit execution authority, idempotency, durable
   journaling, reconciliation, kill-switch tests, and event-risk handling.
4. Consider live execution only after sustained forward-test evidence and a
   separate operational readiness review.

Credentials must come only from external secret storage. Never put an MT5
password, investor password, bridge token, or real-account detail in source
control or this chat.

## Paper-only observation consumer

This engineering demonstration uses `ExperimentalPaperStrategy001`; it is not
research evidence and has no broker-execution authority. Start it in a second
terminal after the read-only bridge:

```zsh
PYTHONPATH=src python3 -m quantforge.application.paper_mt5_runner \
  --symbol XAUUSD \
  --observation-log data/paper_mode/mt5_observations.sqlite3 \
  --journal data/paper_mode/experimental_paper_journal.sqlite3 \
  --kill-switch-file data/paper_mode/KILL_SWITCH \
  --poll-seconds 1
```

It logs `PAPER MODE ONLY` on startup and one decision line per new observation.
The paper portfolio exists only in Python; it is not the observed MT5 account
or its positions. The observation database is
`data/paper_mode/mt5_observations.sqlite3`; the paper journal is
`data/paper_mode/experimental_paper_journal.sqlite3`.

- Activate the kill switch with `touch data/paper_mode/KILL_SWITCH`.
- Stop either process safely with `Ctrl-C`; stop the paper consumer first.
- Inspect the paper lifecycle in the SQLite journal. It records intent, risk,
  approval, and paper execution outcomes. The bridge has no order route and
  the EA has no MT5 trade operation.
