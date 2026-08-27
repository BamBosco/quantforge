# HFM MT5 read-only evidence collection

This track is isolated from AssexMarkets, Dukascopy, and Candidate 006. It
uses the existing `QuantForgeReadOnlyBridge` EA and receiver unchanged. No
receiver option enables order submission; both processes are observation-only.

## Isolated paths

| Instrument | Receiver | Database | Guard |
| --- | --- | --- | --- |
| EURUSD | `127.0.0.1:8768` | `data/hfm_eurusd/mt5_observations.sqlite3` | `--expected-symbol EURUSD` |
| XAUUSD | `127.0.0.1:8769` | `data/hfm_xauusd/mt5_observations.sqlite3` | `--expected-symbol XAUUSD` |

Create the directories before starting the receivers:

```zsh
mkdir -p data/hfm_eurusd data/hfm_xauusd
export QUANTFORGE_MT5_BRIDGE_TOKEN="$(tr -d '\r\n' < data/paper_mode/.mt5_bridge_token)"
```

Start each receiver in a separate terminal:

```zsh
cd ~/Documents/ChatGPT/Project
PYTHONPATH="$PWD/src" .venv/bin/python -m quantforge.infrastructure.mt5.read_only_bridge \
  --host 127.0.0.1 --port 8768 \
  --observation-log data/hfm_eurusd/mt5_observations.sqlite3 \
  --expected-symbol EURUSD
```

```zsh
cd ~/Documents/ChatGPT/Project
PYTHONPATH="$PWD/src" .venv/bin/python -m quantforge.infrastructure.mt5.read_only_bridge \
  --host 127.0.0.1 --port 8769 \
  --observation-log data/hfm_xauusd/mt5_observations.sqlite3 \
  --expected-symbol XAUUSD
```

## MT5 operator steps

1. In HFM MT5, keep the `HFMMarketsGlobal-Demo` account selected.
2. In **Tools → Options → Expert Advisors**, allow WebRequest URLs
   `http://127.0.0.1:8768` and `http://127.0.0.1:8769`.
3. Open separate M1 charts for the exact symbols `EURUSD` and `XAUUSD`.
4. Attach the existing `QuantForgeReadOnlyBridge` EA to each chart.
5. On EURUSD set `BridgeUrl` to
   `http://127.0.0.1:8768/v1/mt5/snapshots` and `SymbolToReport` to `EURUSD`.
6. On XAUUSD set `BridgeUrl` to
   `http://127.0.0.1:8769/v1/mt5/snapshots` and `SymbolToReport` to `XAUUSD`.
7. Paste the private token into each EA's `BridgeToken` input. Never store it
   in source, screenshots, Git, or chat.
8. Set `HeartbeatSeconds` to 30 or greater. Do not switch a running instance
   between symbols or endpoints.
9. Leave live execution disabled. The EA has no order API, but do not enable
   unrelated trading automation in the terminal.

Verify health without credentials:

```zsh
curl -sS http://127.0.0.1:8768/healthz
curl -sS http://127.0.0.1:8769/healthz
```

Then verify each database contains only its guarded symbol:

```zsh
sqlite3 data/hfm_eurusd/mt5_observations.sqlite3 \
  "SELECT broker_symbol, COUNT(*) FROM observation_event GROUP BY broker_symbol;"
sqlite3 data/hfm_xauusd/mt5_observations.sqlite3 \
  "SELECT broker_symbol, COUNT(*) FROM observation_event GROUP BY broker_symbol;"
```

## Evidence status

HFM's public pages confirm MT5 for Forex and Metals and publish server time as
GMT+2 in winter/GMT+3 in summer, with DST on the last Sundays of March and
October. They do not authoritatively establish current demo-server names,
exact symbol suffixes, XAUUSD breaks/rollover/holidays, numeric margin tiers,
or EA permissions.

Screenshots supplied on 2026-08-27 directly show a Demo Premium account on
`HFMMarketsGlobal-Demo` with displayed leverage 1:1000. They show XAUUSD
contract size 100, USD margin/profit, tick size 0.01, tick value 0.1, and
volume 0.01–100 by 0.01; EURUSD shows contract size 100,000 EUR, EUR margin,
USD profit, and volume 0.01–500 by 0.01. These are account/server-specific
MT5 observations and must be confirmed by authenticated receipts.

No HFM live observation has yet been collected. The path becomes ready for
read-only observation only after the two receivers are started and the EA
instances send authenticated snapshots. Collection does not authorize or
enable trading.
