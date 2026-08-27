# External XAUUSD repository review

Date: 2026-08-27. These projects were reviewed as references only. None is
evidence that a strategy is profitable, broker-compatible, or production-safe.
QuantForge remains the source of truth for Candidate 006.

| Repository | Useful reference | Do not copy directly |
| --- | --- | --- |
| `3aLaee/xauusd-trading-bot` | Simple MACD/price-action baseline and explicit dry-run warning | Fixed 15-pip stop, 10-pip target, and London-session claim are unvalidated and instrument/broker dependent |
| `phatnomenal/blackXAU_AUTOMATED-BOT-TRADE` | H4 zone → M5 breakout/retest decomposition; spread and news checks; risk-sizing separation | Automated MQL5 execution, trailing parameters, and defaults require independent replay and broker evidence |
| `0xagarg/xau-ai-trading-bot` | Separation of feature engineering, regime detection, signal filters, risk, sessions, logging, and dashboard | Reported backtest metrics are not independently reproducible here; Kelly sizing, auto-retraining, and live MT5 execution are not approved |
| `codebytemirza/XAUUSD_TRADING_ASISTENT_AI` | Multi-timeframe analysis, ATR/RSI/EMA indicators, dashboard, and AI commentary concepts | LLM suggestions and claimed accuracy are not risk authorization or execution evidence |
| `francomascareloai/EA_SCALPER_XAUUSD` | Honest research status, explicit restrictions, and separation of public MQL5 study code from private execution work | It explicitly is not production-ready and prohibits broker-connected use in its restrictions |
| `ccxt/binance-trade-bot` | Educational example of exchange abstraction and fee-aware decision logic | Binance/crypto-only; irrelevant to MT5 XAUUSD execution |
| `Lokkesh1991/goldbot-all-in-one` | Repository link supplied for possible later inspection | README was not available through the repository endpoint during this review; no claims are made about its implementation |

## What belongs in QuantForge

The safe reuse order is:

1. Extract strategy hypotheses as versioned research studies.
2. Replay them against the frozen XAUUSD source-clock data without changing the
   raw file.
3. Include spread, slippage, session, and missing-data assumptions explicitly.
4. Route any paper signal through the existing readiness and risk gates.
5. Reconcile simulated lifecycle events and preserve an audit trail.

TradingAgents may later provide structured market-context commentary. It must
not set position size, approve an order, alter a policy, or bypass the risk
gate. Freqtrade is useful as a dry-run/backtest/reporting design reference, but
its exchange adapters do not apply to AssexMarkets MT5. Superalgos is deferred
to visualization/data-pipeline work. The Binance bot remains educational only.

## Decision

Do not clone or deploy these bots into the Candidate 006 execution path. The
highest-value next implementation is one QuantForge-native, replayable strategy
study at a time, beginning with the H4/M5 breakout-retest hypothesis if the
owner wants that specific research direction.
