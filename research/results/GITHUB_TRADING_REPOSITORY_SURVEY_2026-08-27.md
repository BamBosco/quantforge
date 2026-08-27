# GitHub trading-repository survey

Date: 2026-08-27. Twenty-six public repositories were reviewed for
Candidate 006. No repository was cloned or executed. README claims are not
treated as proof of profitability, broker compatibility, security, or
production readiness.

## Adoption matrix

| # | Repository | Area | Decision |
|---:|---|---|---|
| 1 | [geraked/metatrader5](https://github.com/geraked/metatrader5) | MQL5 indicators/EAs | Borrow indicator/tester patterns only |
| 2 | [EarnForex/PositionSizer](https://github.com/EarnForex/PositionSizer) | MT5 position sizing | Reimplement concepts against broker tick/margin facts |
| 3 | [yulz008/GOLD_ORB](https://github.com/yulz008/GOLD_ORB) | XAUUSD ORB | Study session/risk structure; reject parameters |
| 4 | [EA31337/EA31337-classes](https://github.com/EA31337/EA31337-classes) | MQL framework | Study APIs; GPLv3 and integration cost require review |
| 5 | [EarnForex/Account-Protector](https://github.com/EarnForex/Account-Protector) | Account safety | Reproduce independent kill-switch concepts |
| 6 | [sajidmahamud835/grid-master-pro-mt5-ea](https://github.com/sajidmahamud835/grid-master-pro-mt5-ea) | Grid/risk controls | Study failure cases; reject grid strategy |
| 7 | [TheSnowGuru/PyTrader-python-mt4-mt5-trading-api-connector-drag-n-drop](https://github.com/TheSnowGuru/PyTrader-python-mt4-mt5-trading-api-connector-drag-n-drop) | Python/MT5 bridge | Study bridge shape; reject as dependency |
| 8 | [darwinex/dwxconnect](https://github.com/darwinex/dwxconnect) | MT bridge/execution | Study callbacks/recovery; do not replace current read-only bridge |
| 9 | [Ichinga-Samuel/aiomql](https://github.com/Ichinga-Samuel/aiomql) | Async MT5 | Possible isolated adapter pilot after audit |
| 10 | [ilahuerta-IA/mt5_live_trading_bot](https://github.com/ilahuerta-IA/mt5_live_trading_bot) | Python MT5 lifecycle | Borrow state-machine and sizing tests |
| 11 | [Quantreo/MetaTrader-5-AUTOMATED-TRADING-using-Python](https://github.com/Quantreo/MetaTrader-5-AUTOMATED-TRADING-using-Python) | MT5 education | Tutorial reference only |
| 12 | [jimtin/algorithmic_trading_bot](https://github.com/jimtin/algorithmic_trading_bot) | MT5 tutorials | Borrow small patterns only |
| 13 | [codedpro/mt5-trade-split-manager](https://github.com/codedpro/mt5-trade-split-manager) | Agent/execution EA | Study order splitting; keep agents away from authority |
| 14 | [edtechre/pybroker](https://github.com/edtechre/pybroker) | Backtesting/ML | Borrow walk-forward/bootstrap/slippage patterns; license review |
| 15 | [polakowo/vectorbt](https://github.com/polakowo/vectorbt) | Vector research | Borrow parameter-sweep ideas; not execution simulation |
| 16 | [kernc/backtesting.py](https://github.com/kernc/backtesting.py) | Backtesting | Best candidate for an isolated research dependency |
| 17 | [mementum/backtrader](https://github.com/mementum/backtrader) | Event backtesting | Borrow order/commission models; avoid core adoption |
| 18 | [josephchenhk/qtrader](https://github.com/josephchenhk/qtrader) | Event-driven engine | Borrow same-code simulation/live concepts |
| 19 | [gbeced/basana](https://github.com/gbeced/basana) | Async feeds/execution | Borrow feed reconciliation concepts; crypto-centric |
| 20 | [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) | Dry-run/backtesting | Borrow operational patterns; crypto-only adapters |
| 21 | [cvxgrp/cvxportfolio](https://github.com/cvxgrp/cvxportfolio) | Portfolio optimization | Borrow causal cost constraints; GPLv3 and overkill for one instrument |
| 22 | [dcajasn/Riskfolio-Lib](https://github.com/dcajasn/Riskfolio-Lib) | Risk analytics | Optional offline analytics dependency after license/dependency review |
| 23 | [ranaroussi/yfinance](https://github.com/ranaroussi/yfinance) | Market data | Reject as authoritative XAUUSD source |
| 24 | [quantopian/zipline](https://github.com/quantopian/zipline) | Legacy backtesting | Reject as core dependency |
| 25 | [quantopian/pyfolio](https://github.com/quantopian/pyfolio) | Legacy reporting | Borrow report ideas; reject old dependency stack |
| 26 | [AI4Finance-Foundation/FinRL](https://github.com/AI4Finance-Foundation/FinRL) | RL research | Research inspiration only; no live authority |

## What can actually finish QuantForge

The repository landscape does not remove the unresolved external facts:
AssexMarkets historical server/DST/export convention, XAUUSD schedule and
rollover, broker margin behavior, and statistically meaningful execution
deviation. No open-source README can establish those facts for this account.

The highest-value controlled reuse is:

1. Keep QuantForge's existing MT5 observation, risk, paper, reconciliation, and
   audit path as the source of truth.
2. Use `backtesting.py` concepts for one isolated XAUUSD replay adapter, with
   broker-specific spread, tick-value, commission, slippage, and stop models.
3. Borrow walk-forward/bootstrap ideas from PyBroker/vectorbt without adopting
   their execution assumptions.
4. Borrow state-machine and broker-derived sizing tests from the MT5 Python
   projects.
5. Add TradingAgents/FinRL-style outputs only as non-authoritative research
   evidence.

Do not merge turnkey EAs, grid/martingale logic, fixed pip defaults, Kelly
sizing, claimed win rates, auto-retraining, or live order connectors into
Candidate 006.

## Fixed decision

No external repository is adopted as a second source of truth or direct
production-execution dependency. Future reuse must be a small, pinned,
license-reviewed component with tests and a QuantForge adapter. This decision
is intentionally stable so repository discovery does not reset the project
completion estimate.
