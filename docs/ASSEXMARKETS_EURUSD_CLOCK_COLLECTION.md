# AssexMarkets EURUSD clock-evidence collection

EURUSD is a parallel **read-only infrastructure evidence** stream. It is not a
Candidate 006 instrument and does not transfer a forex session rule to XAUUSD.
Its purpose is to compare AssexMarkets' published forex server-time schedule
with independently observed MT5 server/local/UTC clocks.

## Isolation contract

| Scope | Value |
| --- | --- |
| Broker server | `AssexmarketsGlobal-Trade` |
| Instrument | `EURUSD`, M1 |
| Local bridge | `127.0.0.1:8767` |
| Receipt database | `data/assexmarkets_eurusd/mt5_observations.sqlite3` |
| Candidate 006 audit | Not attached |
| Broker execution | Disabled; the EA has no order operation |

This database must not be mixed with the XAUUSD Candidate 006 database,
Dukascopy data, or the contaminated historical `:8765` log.

## Start the parallel receiver

The receiver uses the existing private local bridge token without printing it:

```zsh
cd ~/Documents/ChatGPT/Project
export QUANTFORGE_MT5_BRIDGE_TOKEN="$(tr -d '\r\n' < data/paper_mode/.mt5_bridge_token)"
PYTHONPATH="$PWD/src" .venv/bin/python -m quantforge.infrastructure.mt5.read_only_bridge \
  --host 127.0.0.1 \
  --port 8767 \
  --observation-log data/assexmarkets_eurusd/mt5_observations.sqlite3
```

The running receiver is read-only and accepts no broker-order endpoint.

## MT5 attachment

On the same `AssexmarketsGlobal-Trade` demo terminal:

1. In **Tools → Options → Expert Advisors**, add
   `http://127.0.0.1:8767` to the WebRequest allow-list; keep the existing
   `:8766` entry for XAUUSD.
2. Open `EURUSD` on M1 and attach another instance of the compiled existing
   `QuantForgeReadOnlyBridge` EA.
3. Set `BridgeUrl` to
   `http://127.0.0.1:8767/v1/mt5/snapshots`, `SymbolToReport` to `EURUSD`,
   and `HeartbeatSeconds` to `30` or greater.
4. Paste the existing private bridge token into this EA instance's
   `BridgeToken` input. Do not put it in source code, a screenshot, Git, or
   chat.
5. Confirm the EA's **Common** tab allows algorithmic trading only for this
   non-submitting EA. Do not enable any broker execution setting.

The terminal should remain quiet on successful posts. Verify collection from
the dedicated database, not terminal text.

## Evidence review

After accepted receipts arrive, inspect provenance using the existing generic
tool:

```zsh
PYTHONPATH=src .venv/bin/python tools/inspect_mt5_time_provenance.py \
  data/assexmarkets_eurusd/mt5_observations.sqlite3
```

Compare the raw `time_provenance` fields with XAUUSD evidence. Common
broker-infrastructure evidence may establish the current server clock only.
EURUSD's documented forex trading hours, rollover and GMT+0 wording cannot be
silently applied to XAUUSD metals or to historical XAUUSD bars.

For a reproducible coverage summary, run:

```zsh
PYTHONPATH=src .venv/bin/python tools/analyze_assexmarkets_eurusd.py \
  data/assexmarkets_eurusd/mt5_observations.sqlite3
```

## Required coverage

Collect fresh accepted receipts at ordinary market periods and, over time,
around the forex daily break, Friday close, Sunday/Monday open, and DST
boundaries. Preserve receipt IDs, broker name, quote/bars, and provenance.
Do not fabricate a break, a timestamp, or a broker fill.
