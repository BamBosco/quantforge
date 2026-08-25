# Intraday Momentum — Initial Source Review

## Status

**Research reference only. No source below validates a Headway Demo `XAUUSD`
strategy or supplies QuantForge trading rules.**

## Sources reviewed

| Source | Market and data | Relevant finding | QuantForge limitation |
| --- | --- | --- | --- |
| [Heston, Korajczyk & Sadka (2010), *Intraday Patterns in the Cross-Section of Stock Returns*](https://doi.org/10.1111/j.1540-6261.2010.01573.x) | NYSE-listed stocks; half-hour intervals; cross-sectional portfolios | Documents predictable same-time-of-day return patterns and distinguishes short-horizon microstructure reversal from longer-horizon continuation. | Cross-sectional equities are not a single gold CFD. Its portfolio construction, exchange quotes, and sample are not portable rules. |
| [Elaut, Lampaert & Frömmel (2018), *Intraday Momentum in FX Markets*](https://biblio.ugent.be/publication/8060014) | Transaction-level RUB/USD data on the Moscow Interbank Currency Exchange, 2005–2014 | Studies the link between early and late returns in an FX market with explicit trading hours; examines liquidity-provider behaviour. | RUB/USD, a central trading venue, and transaction-level data differ materially from OTC-style XAUUSD CFD M1 bars. No transfer is assumed. |
| [Lai et al. (2022), *Market Intraday Momentum with New Measures for Trading Cost*](https://doi.org/10.3390/jrfm15110523) | KOSPI index; 30-minute observations; estimated cost measures | Treats transaction cost as central to assessing an intraday momentum claim. | A stock-index study and its cost proxies do not replace Headway’s recorded spread or validate gold-CFD execution. |

## What this changes for QuantForge

1. Intraday momentum is a legitimate **research hypothesis**, not a claim of
   profitability.
2. The implementation must model recorded bid/ask spread and adverse
   slippage. It must not substitute estimated equity-market costs.
3. The candidate must avoid order-flow claims because the present dataset is
   M1 OHLC, not transaction-level or order-book data.
4. A single-instrument XAUUSD test needs a deterministic directional signal;
   it cannot copy cross-sectional stock ranking methodology.
5. The standard chronological validation protocol, including its separate
   holdout and cost-stress controls, applies before any promotion decision.

## Research gap before specification

No exact signal, threshold, entry, stop, holding period, or session has been
chosen. These must be defined in a proprietary `INTRADAY_MOMENTUM.md`
specification, reviewed for look-ahead bias, and approved before implementation
or backtesting. Combining several academic variations or selecting values after
seeing results is prohibited.
