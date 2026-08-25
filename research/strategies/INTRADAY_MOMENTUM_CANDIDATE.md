# Intraday Momentum — Research Candidate

## Status

**Experiment 001 rejected and frozen.** The approved fixed specification was
implemented and evaluated once. It failed the standard research gate; see the
[result](../results/INTRADAY_MOMENTUM_XAUUSD_HEADWAY_DEMO_M1_REPLAY_2026-08-14.md).
No paper or live trading is authorised.

## Selection decision

Intraday momentum is the next QuantForge research direction for Headway Demo
`XAUUSD`. This is a new candidate, not another modification of Opening Range
Breakout (ORB). Both fixed ORB experiments remain rejected and frozen.

The initial question is deliberately narrow:

> Does a predeclared intraday price-momentum hypothesis for Headway Demo
> `XAUUSD` show an economically robust distribution after recorded spread and
> adverse-slippage stress?

No answer is assumed. The null hypothesis is that any apparent intraday
momentum performance is noise or disappears under realistic costs.

## Why this direction was chosen

The accepted local dataset contains continuous M1 OHLC, tick activity, and
per-bar spread observations. It can support price-return, time-of-day,
volatility, and cost research with explicit M1 limitations.

The dataset does not support several other candidate families honestly:

| Candidate family | Current decision | Reason |
| --- | --- | --- |
| Another ORB variation | Rejected | The baseline and its directional variant failed; further tuning would be data mining. |
| VWAP | Deferred | Exchange-volume is zero throughout the MT5 export. Tick activity must not be presented as true exchange volume. |
| Order flow | Deferred | M1 OHLC cannot reconstruct tick sequence, order-book imbalance, or trade direction. |
| Market profile | Deferred | It may be researched later as time-at-price, but its exact rules and source basis are not yet documented. |
| Intraday momentum | Selected for research | Price and spread data are available; the hypothesis can be stated without claiming unavailable volume or order-flow information. |

## Required work before any implementation

1. Continue reviewing primary academic/reproducible sources on intraday
   momentum. The initial source review is recorded in
   [research/papers/INTRADAY_MOMENTUM_SOURCE_REVIEW.md](../papers/INTRADAY_MOMENTUM_SOURCE_REVIEW.md).
   Each review must record market, sample, data frequency, costs, methodology,
   limitations, and portability to a gold CFD.
2. Review the proposed [intraday-momentum specification](INTRADAY_MOMENTUM.md).
   It defines one exact proprietary hypothesis, including the instrument,
   session, signal observation window, holding period, entry, stop, exit,
   no-trade conditions, and every parameter.
3. State the economic rationale and all assumptions that have not been tested.
4. Predeclare its data-quality rules and use the standard chronological
   validation protocol before running a replay.
5. Obtain explicit approval of the finished specification before strategy code
   or a backtest is created.

## Non-negotiable boundaries

- Tick volume is not exchange volume and cannot justify a volume-weighted
  signal.
- M1 OHLC does not reveal intrabar order; ambiguous fills must remain excluded
  unless tick data resolves them.
- No threshold search, indicator shopping, or selection based on the rejected
  ORB results.
- The Risk Engine remains the only authority for any future sizing, approval,
  cancellation, or flattening decision.
