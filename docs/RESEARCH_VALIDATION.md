# Research Validation Framework

## Purpose

This framework is the shared evidence gate for every QuantForge strategy
candidate. It evaluates a fixed strategy specification; it does not search for
parameters, select a favourable subset, calculate position size, or authorise
trading.

## Required sequence

1. Freeze the strategy specification, dataset manifest, costs, and research
   protocol before a replay.
2. Evaluate all eligible sessions chronologically.
3. Reserve the final contiguous portion as the untouched holdout period.
4. Build walk-forward training/validation windows only in the development
   portion.
5. Evaluate every configured cost scenario on identical development-session
   dates; report the full sample separately.
6. Apply the versioned research gate.
7. Retain both positive and negative reports with their configuration and data
   identities.

Passing the research gate permits only an independent confirmation study. It
does not permit paper trading, broker connectivity, or live capital.

## Shared measures

Results remain in normalized R, not currency. The framework reports completed
trades, wins/losses, total and mean R, maximum cumulative-R drawdown, profit
factor, chronological holdout performance, and cost-scenario comparability.

Walk-forward windows are chronological and have no future information. For a
fixed, non-fitted rule they assess stability across time; a future fitted model
must fit only within each training window before its validation window is
evaluated.

## Current standard protocol

The initial versioned protocol is
[`config/research/standard_validation_protocol.toml`](../config/research/standard_validation_protocol.toml).
Its numbers are configuration, not constants in strategy code. It requires
positive total and mean R across all cost scenarios, positive holdout results,
and the configured number of positive walk-forward validation windows.

Monte Carlo and bootstrap analysis are deliberately not represented as a
promotion shortcut. They remain a later validation addition and must preserve
the same dataset and cost provenance.

## Non-trading forecast studies

Directional strategy validation uses normalized R. A non-trading forecast study
uses an explicitly documented forecast score and baseline instead; it cannot
inherit an R-multiple promotion result. The first such study is the
[`XAUUSD Intraday Volatility Regime`](../research/strategies/XAUUSD_INTRADAY_VOLATILITY_REGIME.md).
Its initial pass permits independent confirmation only and has no Risk Engine
or trading authority.
