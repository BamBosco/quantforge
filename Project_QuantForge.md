# Project QuantForge

## Mission

Build durable, explainable quantitative-trading software that protects capital
first. Profit is an outcome of validated research, disciplined risk controls,
and reliable operations—not the objective that overrides them.

## Scope

QuantForge will support research, historical simulation, controlled forward
testing, portfolio/risk control, execution adapters, accounting, and analysis.
It begins as a Python modular monolith with SQLite for local durable state.

## Non-goals for Version 0.1

- No live trading or live credentials.
- No strategy claims or performance promises.
- No machine-learning component without a defined hypothesis and evaluation plan.

## Domain knowledge

The version-controlled [research corpus](research/README.md) contains market
concepts, quantitative research, and proprietary strategy documentation. It
must be studied before strategy work. Proprietary rules take precedence over
generic trading knowledge, but never over QuantForge's risk, security, or
validation policies. ORB is the first strategy candidate, not a production
strategy.

## Engineering invariants

1. Every order originates as an immutable trade intent.
2. Only the Risk Engine may turn an intent into an approved order.
3. Execution adapters accept approved orders only.
4. Inputs, decisions, and outcomes are auditable and replayable.
5. Research artifacts cannot directly activate production trading.

Further detail lives in the architecture, risk, security, data-governance,
and forward-testing specifications.
