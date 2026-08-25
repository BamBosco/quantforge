# Backtesting

Backtests are deterministic event replays, not proof of an edge. Each run
records code revision, dependency lock state, configuration, random seed,
dataset manifest, execution assumptions, and complete results.

Required safeguards include no look-ahead bias, no survivorship bias where
applicable, realistic spreads/fees/slippage/latency assumptions, order lifecycle
simulation, and out-of-sample analysis. Evaluate drawdown, expectancy, profit
factor, Sharpe/Sortino, exposure, turnover, tail loss, and sensitivity to costs.

Promotion requires walk-forward and Monte Carlo analysis; performance alone is
never sufficient.

The shared chronological split, walk-forward, cost-stress, drawdown, and
research-gate implementation is documented in
[Research Validation Framework](RESEARCH_VALIDATION.md). Passing it permits
only independent confirmation work.

The first implemented research baseline is documented in
[`research/strategies/ORB_BACKTEST_DESIGN.md`](../research/strategies/ORB_BACKTEST_DESIGN.md).
It is offline only and requires complete, validated local historical data.

## MT5 exports

The Headway demo MT5 Bars export supplies timezone-naive wall-clock timestamps,
not UTC timestamps. On 2026-08-14 its newest row matched the connected Mac's
clock exactly, so every export records the Mac timezone in its own immutable
dataset manifest. The import boundary requires that timezone explicitly and
normalizes data to UTC before strategy calculation. A broker chart-server clock
must never be substituted for the export timestamp timezone.

## ORB event replay

The initial ORB simulator is offline and non-sized. It creates an OCO pair only
after the opening range closes, routes both order shapes through the protective
stop validator, applies recorded bid/ask spread plus configured adverse
slippage, atomically cancels the peer after a fill, and closes a surviving
position at 13:30 New York time. A bar that could touch both OCO entries, or an
entry and its protective stop, is reported as ambiguous rather than assigned an
invented fill sequence. Any missing M1 bar between 08:20 and the forced-exit
bar invalidates that session.

The first reproducible replay result is recorded in
[`research/results/ORB_XAUUSD_HEADWAY_DEMO_M1_INITIAL_REPLAY_2026-08-14.md`](../research/results/ORB_XAUUSD_HEADWAY_DEMO_M1_INITIAL_REPLAY_2026-08-14.md).
It was withdrawn after timestamp provenance was corrected. The current
three-year replay is recorded in
[`research/results/ORB_XAUUSD_HEADWAY_DEMO_M1_THREE_YEAR_REPLAY_2026-08-14.md`](../research/results/ORB_XAUUSD_HEADWAY_DEMO_M1_THREE_YEAR_REPLAY_2026-08-14.md).
The separate overnight-directional experiment also failed its research gate:
[`research/results/ORB_XAUUSD_HEADWAY_DEMO_OVERNIGHT_BIAS_REPLAY_2026-08-14.md`](../research/results/ORB_XAUUSD_HEADWAY_DEMO_OVERNIGHT_BIAS_REPLAY_2026-08-14.md).
No result authorizes any trading mode.

## Intraday Momentum replay

Intraday Momentum Experiment 001 is a separate, price-only market-entry
replay. It uses a predeclared 30-minute signal, the shared protective-stop
validator, recorded bid/ask spread, adverse slippage sensitivity, and explicit
M1 ambiguity exclusions. Its complete result is retained in
[`research/results/INTRADAY_MOMENTUM_XAUUSD_HEADWAY_DEMO_M1_REPLAY_2026-08-14.md`](../research/results/INTRADAY_MOMENTUM_XAUUSD_HEADWAY_DEMO_M1_REPLAY_2026-08-14.md).
It failed the research gate and is frozen; the simulator is audit tooling, not
an execution feature.
