# Candidate 006 second-broker evidence collection

This is a read-only collection procedure. It creates no order, and it must use
a distinct observation log and audit database from the existing Dukascopy run.

## Start the receiver

```zsh
cd ~/Documents/ChatGPT/Project
export QUANTFORGE_MT5_BRIDGE_TOKEN='store outside the repository'
PYTHONPATH=src python3 -m quantforge.infrastructure.mt5.read_only_bridge \
  --port 8766 \
  --observation-log data/candidate_006_second_broker/mt5_observations.sqlite3 \
  --expected-symbol XAUUSD
```

Attach `QuantForgeReadOnlyBridge` to the second broker's XAUUSD M1 chart with
the same loopback URL and the token held only in the terminal and EA input.
Keep `live_trading_enabled`, `order_submission_enabled`, and every send flag
false. Capture the broker server name in the receipt; it is the immutable
broker identity used for later separation and audit.

The EA is single-symbol/single-endpoint. For simultaneous EURUSD clock
collection and XAUUSD Candidate 006 collection, use two charts and two EA
instances in the same MT5 terminal: keep EURUSD pointed exclusively at
`http://127.0.0.1:8767/v1/mt5/snapshots`, and configure this XAUUSD instance
exclusively for `http://127.0.0.1:8766/v1/mt5/snapshots`. Do not switch one
instance between symbols or endpoints.

`QuantForgeReadOnlyBridge` version 1.01 additionally records MT5 server,
terminal-local, and UTC clocks in each receipt's `time_provenance` object. It
does not change the bridge endpoint, authentication, or read-only boundary.
After compiling and reattaching that EA version, collect a fresh accepted
receipt to establish the current server-to-UTC offset. Five accepted receipts
collected on 2026-08-26 measured the server at UTC+3, terminal-local time at
UTC+1, and the terminal UTC clock exactly. Repeat around a DST boundary before
asserting the historical export's DST convention.

The optional receiver `--expected-symbol XAUUSD` guard rejects authenticated
EURUSD payloads before they enter the Candidate 006 database.

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

## Inspecting fresh time provenance

After compiling and attaching the EA v1.01 or higher, use the repository helper
below to summarize the raw `time_provenance` fields from any fresh SQLite or
JSONL evidence set:

```zsh
PYTHONPATH=src python3 tools/inspect_mt5_time_provenance.py \
  data/candidate_006_second_broker/mt5_observations.sqlite3
```

This reports the raw terminal server/local/UTC clocks and the delta relative to
`observed_at_utc` so the broker offset and any DST discontinuity can be reviewed
without guessing.
