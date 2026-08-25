# Opening Range Breakout (ORB) — Strategy Candidate

## Status

**Baseline frozen after failing its robustness gate. Not approved for paper or
live trading.**

ORB observes the price range formed during a defined opening period and tests
whether a move beyond that range, subject to predeclared filters and execution
assumptions, has a statistically useful distribution of outcomes.

## Required specification before implementation

The proprietary rules for this candidate have not yet been provided. Before
code is created, this document must define:

- Instrument universe, exchange/session calendar, timezone, and opening window.
- Range construction, breakout definition, entry timing, and order type.
- Long/short eligibility, filters, cancellation conditions, and time exits.
- Stop-loss, target, trailing, and end-of-session rules.
- Treatment of gaps, halts, missing data, spread, slippage, fees, and partial fills.
- All configurable parameters, defaults, permitted ranges, and rationale.
- Position-risk assumptions and any correlation restrictions.
- Dataset requirements, in-sample/out-of-sample protocol, benchmarks, and
  promotion/failure criteria.

## Source status

The Toby Crabel primary source is now available for a complete structured
review. The relevant Thomas Bulkowski chapter has not yet been added. The supplied file named
`447611148-swing-and-day-trading-evolution-of-a-trader.pdf` is a three-page
download/advertisement page, not the requested book content; it is excluded as
an ORB reference. This candidate must not inherit rules from summaries or an
AI's memory in place of reviewed, version-controlled rules.

The primary-source findings and the decisions that remain open are maintained
in [Crabel ORB review](../notes/CRABEL_ORB_REVIEW.md) and the
[ORB decision sheet](ORB_DECISION_SHEET.md). Those documents deliberately
separate the source-inspired hypothesis from QuantForge's eventual rules.

## Non-negotiable implementation constraints

- The strategy may emit only a `TradeIntentGenerated` message; it cannot size
  positions or submit orders.
- The Risk Engine performs sizing and can reject every intent.
- Every result must be reproducible from a dataset manifest, configuration,
  code revision, and execution assumptions.
- A positive backtest is evidence to investigate, not permission to trade.

## Approved baseline

The initial research baseline is Headway Demo `XAUUSD`, a 15-minute opening
range starting at 08:20 `America/New_York`, two-sided OCO stop entries using a
ten-session Crabel Stretch buffer, an opposite-range protective stop, one entry
per session, and a 13:30 New York forced exit. See the versioned
[configuration](../../config/strategies/orb_xauusd_headway_demo_baseline.toml)
and [backtest design](ORB_BACKTEST_DESIGN.md) for exact definitions.

Its three-year replay is effectively flat before extra slippage and negative
after one additional point of adverse slippage. It must remain unchanged; see
the [replay result](../results/ORB_XAUUSD_HEADWAY_DEMO_M1_THREE_YEAR_REPLAY_2026-08-14.md).
The separately governed [directional-bias experiment](ORB_EXPERIMENT_002_PROPOSAL.md)
has also failed its research gate and is frozen. Its
[result report](../results/ORB_XAUUSD_HEADWAY_DEMO_OVERNIGHT_BIAS_REPLAY_2026-08-14.md)
does not authorise any tuning or promotion.

## Approval gate

After the missing rules are supplied, QuantForge must review the full
specification, list every untested assumption, propose a module design, and
receive explicit approval before any ORB strategy code is written.

## Initial venue boundary

Headway Demo `XAUUSD` is the candidate paper-testing symbol. Exness `XAUUSDm`
and `XAUUSDc` are distinct broker/account profiles and require their own
configuration and validation; no results are assumed portable between them.
