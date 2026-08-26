# Candidate 006 second-broker evidence collection

This is a read-only collection procedure. It creates no order, and it must use
a distinct observation log and audit database from the existing Dukascopy run.

## Start the receiver

```zsh
cd ~/Documents/ChatGPT/Project
export QUANTFORGE_MT5_BRIDGE_TOKEN='store outside the repository'
PYTHONPATH=src python3 -m quantforge.infrastructure.mt5.read_only_bridge \
  --observation-log data/candidate_006_second_broker/mt5_observations.sqlite3
```

Attach `QuantForgeReadOnlyBridge` to the second broker's XAUUSD M1 chart with
the same loopback URL and the token held only in the terminal and EA input.
Keep `live_trading_enabled`, `order_submission_enabled`, and every send flag
false. Capture the broker server name in the receipt; it is the immutable
broker identity used for later separation and audit.

## Required collection coverage

Collect accepted receipts over normal, stressed, rollover, scheduled-news,
and representative-session periods. The EA receipt records bid/ask/spread,
UTC timestamp, completed M1 bar, account equity, volume bounds, contract and
tick specifications, filling/order/trade modes, stop/freeze levels, current
positions/orders, and recent deal facts. Record the broker's published trading
hours, server timezone, DST behavior, holiday schedule, rollover time, and
margin rules alongside the frozen package.

Do not infer execution quality from quotes. Reference price, observed quote,
paper/simulated price, latency, adverse movement, slippage, and rejection
conditions remain separately labelled simulation evidence until independent
broker execution evidence is authorized.

## Freeze and review

Export only after the collection interval is complete. The existing evidence
package exporter hashes accepted receipt-linked records and its manifest; use a
separate immutable destination for the second broker. A policy may be promoted
only after review ties its value to this broker identity, source receipts, and
the required spread, session, risk, or execution-quality evidence. Otherwise
it remains provisional with an explicit reason.
