# Candidate 004 — Manual Native XAUUSD M1 Export Procedure

## Preconditions

Use only the `VantageMarkets-Demo` terminal and standard `XAUUSD`. Do not use
`XAUUSD247`, custom symbols, a strategy tester, or any order/trading control.
This procedure exports raw bars only; it does not authorize opening or
inspecting confirmation rows after the export is created.

Before exporting, create the two destinations once:

```zsh
mkdir -p data/candidate_004_vantage_mt5_raw/evaluation data/candidate_004_vantage_mt5_raw/confirmation
```

## 1. Export the evaluation file

1. In MT5, open **View → Symbols** and select standard **XAUUSD**.
2. Select the **Bars** tab.
3. Set timeframe to **M1**.
4. Set the start to `2013.01.02 00:00` and end to `2023.12.29 23:56` exactly as
   terminal-formatted timestamps. Do not reinterpret them as UTC or New York.
5. Click **Request** if MT5 requires it. Do not evaluate or transcribe values
   from the table.
6. Use **Export Bars** and save exactly as:
   `XAUUSD_M1_VantageMarkets_Demo_201301020000_202312292356.csv`.
7. Move the file unchanged to
   `data/candidate_004_vantage_mt5_raw/evaluation/`.
8. In Terminal, calculate its size and SHA-256 without opening it:

   ```zsh
   wc -c data/candidate_004_vantage_mt5_raw/evaluation/XAUUSD_M1_VantageMarkets_Demo_201301020000_202312292356.csv
   shasum -a 256 data/candidate_004_vantage_mt5_raw/evaluation/XAUUSD_M1_VantageMarkets_Demo_201301020000_202312292356.csv
   ```

9. Create the evaluation sidecar manifest using the fields in the pre-export
   record. Record a displayed MT5 coverage range only if the application itself
   shows one as metadata.

## 2. Export and seal the confirmation file

1. Return to **Symbols → Bars**, keep standard `XAUUSD` and M1.
2. Set the start to `2024.01.02 01:00` and end to `2026.08.21 23:56`.
3. Click **Request** only as needed to make the native export available. Do not
   inspect, copy, assess, or analyse displayed rows.
4. Use **Export Bars** and save exactly as:
   `XAUUSD_M1_VantageMarkets_Demo_202401020100_202608212356.csv`.
5. Move the file unchanged to
   `data/candidate_004_vantage_mt5_raw/confirmation/`.
6. Calculate only byte size and SHA-256; do not open the file:

   ```zsh
   wc -c data/candidate_004_vantage_mt5_raw/confirmation/XAUUSD_M1_VantageMarkets_Demo_202401020100_202608212356.csv
   shasum -a 256 data/candidate_004_vantage_mt5_raw/confirmation/XAUUSD_M1_VantageMarkets_Demo_202401020100_202608212356.csv
   ```

7. Create the confirmation sidecar manifest, then seal the file. Do not preview,
   parse, inspect, or otherwise access confirmation rows again.

## Stop condition

After the two checksums and manifests are recorded, stop and report the limited
acquisition metadata specified by the pre-export record. Do not run structural
checks, session counts, signals, returns, trades, strategy work, replay,
backtesting, optimization, tuning, paper trading, MT5 execution, broker
execution, or live trading.
