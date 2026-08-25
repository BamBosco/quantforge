# XAUUSD Intraday Volatility — Source Review

## Purpose

This review supports a **risk-regime research hypothesis**, not a claim that
gold direction is predictable. The proposed work asks whether early-session
realized price movement helps forecast later-session movement for the specific
Headway Demo `XAUUSD` dataset. It does not assume that findings in exchange
traded gold futures transfer directly to a retail CFD.

## Reviewed sources

### Cai, Cheung, and Wong (2001) — COMEX gold futures

- Source: [What moves the gold market?](https://doi.org/10.1002/1096-9934%28200103%2921%3A3%3C257%3A%3AAID-FUT4%3E3.0.CO%3B2-W)
- Market and data: COMEX gold futures, intraday return-volatility analysis.
- Relevant finding: intraday patterns materially affect gold return-volatility
  dynamics; the paper also examines macroeconomic-announcement effects.
- What it supports: separating time-of-day and volatility from directional
  prediction is economically sensible for gold research.
- What it does not support: a specific 08:20–08:50 New York forecast, Headway
  CFD execution, or any trading rule.

### Hauptfleisch et al. (2016) — gold price discovery

- Source: [Who Sets the Price of Gold? London or New York](https://doi.org/10.1002/fut.21775)
- Market and data: London spot and New York futures using intraday data.
- Relevant finding: both venues contribute to gold price discovery, with New
  York futures larger on average in that study.
- What it supports: New York session behaviour is worth studying explicitly.
- What it does not support: that the same pattern exists in the Headway `XAUUSD`
  CFD, or that volatility predicts price direction.

### Watkins et al. (2018) — precious-metal intraday seasonality

- Source: [Intraday seasonality in efficiency, liquidity, volatility and volume: Platinum and gold futures in Tokyo and New York](https://doi.org/10.1016/j.jcomm.2018.05.001)
- Market and data: one-minute gold and platinum futures data in Tokyo and New
  York markets.
- Relevant finding: market microstructure and volatility vary across global
  trading sessions.
- What it supports: fixed session definitions and explicit intraday controls.
- What it does not support: use of exchange-volume or liquidity variables in
  the current export. Headway's exchange-volume field is zero, so this project
  must not reproduce volume-based components with tick activity.

### Wei, Li, and Chen (2023) — intraday gold-volatility forecasting

- Source: [Intraday volatility predictability in China gold futures market](https://doi.org/10.1016/j.frl.2023.104022)
- Market and data: high-frequency China gold futures data with COMEX
  information; predicts later realized volatility, not a CFD trading return.
- Relevant finding: segmented intraday information improved forecasts of later
  realized volatility in that study.
- What it supports: a predeclared volatility-forecasting experiment is a more
  defensible next research step than another unsupported entry rule.
- What it does not support: the proposed model, forecast accuracy, or a live
  risk action for Headway `XAUUSD`.

## Portability limits

- The target is a Headway demo CFD; the sources use exchange-traded futures or
  spot markets with different trading hours, liquidity, and execution rules.
- The local data is M1 bid OHLC plus broker-reported spread. It cannot measure
  realized transaction-level volatility, order flow, exchange liquidity, or
  quote depth.
- Scheduled news is intentionally out of scope for this initial attribution
  study. It must not be treated as controlled merely because it is absent.

## Conclusion

The literature justifies studying time-of-day volatility and risk regimes, not
assuming a tradable directional edge. Any QuantForge result must stand on the
versioned Headway dataset and its own predeclared validation criteria.
