# Research Corpus

## Purpose

This directory contains QuantForge's trading philosophy, market concepts,
quantitative research, and proprietary strategy documentation. Read every
applicable document here before designing or changing a strategy.

These works are research references, not unquestionable truth. Explain the
underlying concept, distinguish a hypothesis from a validated edge, identify
untested assumptions, and never claim profitability without evidence.

## Authority order

1. QuantForge's risk, security, architectural, and validation policies.
2. QuantForge proprietary strategy documentation in this directory.
3. General trading and quantitative-research references.

Proprietary documentation guides strategy design but cannot override the Risk
Engine, security controls, or promotion gates.

## Initial corpus

The corpus may include research associated with Munehisa Homma, Richard
Wyckoff, Charles Dow, Jesse Livermore, W.D. Gann, Van K. Tharp, Ralph Vince,
Mark Douglas, Brett Steenbarger, Nassim Nicholas Taleb, Ernest Chan, and
Marcos López de Prado. Add source-specific documents under `research/` or its
topic subdirectories with provenance and any usage restrictions.

## Directory layout

```text
research/
  books/       Source-specific notes and bibliographic records
  papers/      Academic papers and research summaries
  strategies/  Version-controlled candidate specifications
  notes/       Cross-source research, source intake, and experiment notes
```

Source documents remain outside this repository unless their licensing permits
storage here. Commit concise notes, provenance, and research conclusions—not
unlicensed copies of books or papers.

## Strategy workflow

Opening Range Breakout (ORB) was the first strategy candidate and is frozen
after two failed research experiments. Intraday Momentum Experiment 001 is
also frozen after its fixed replay failed the
[standard research gate](results/INTRADAY_MOMENTUM_XAUUSD_HEADWAY_DEMO_M1_REPLAY_2026-08-14.md).
Any future strategy candidate needs a new written specification, plain-language
explanation, stated parameters and assumptions, architecture review, and
approval before strategy code is written.

The current next research candidate is the non-directional
[XAUUSD Intraday Volatility Regime](strategies/XAUUSD_INTRADAY_VOLATILITY_REGIME.md).
Its initial research gate passed, permitting only independent confirmation;
it is not a trading strategy and not a replacement for the existing Risk
Engine.
