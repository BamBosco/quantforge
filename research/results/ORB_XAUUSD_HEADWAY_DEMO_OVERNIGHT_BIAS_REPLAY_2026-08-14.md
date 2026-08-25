# ORB XAUUSD Headway Demo — Overnight-Bias Replay

## Status

**Failed research gate. Not approved for independent confirmation, paper
trading, or live trading.** The configuration is frozen; no parameter tuning
or follow-up variation is authorised from this result.

## Hypothesis tested

Experiment 002 retained the frozen ORB session, 15-minute range, ten-session
Stretch buffer, protective stop, one-trade limit, 13:30 New York exit, and
cost scenarios. It changed one variable only: entry side eligibility.

- Buy-only when the 08:19 New York M1 close exceeded the 00:00 New York M1
  open.
- Sell-only when the 08:19 close was below the 00:00 open.
- No trade when the two prices were equal or either required M1 bar was absent
  or duplicated.

The exact rule is in the versioned
[experiment configuration](../../config/strategies/orb_xauusd_headway_demo_overnight_bias.toml)
and [proposal](../strategies/ORB_EXPERIMENT_002_PROPOSAL.md).

## Reproducibility record

- Dataset manifest:
  `config/datasets/headway_demo_xauusd_m1_20230814_20260814.toml`
- Dataset checksum verified before replay:
  `488fa6147f1814b6671e67f853ed59d796e227b87c9f7004626ccd30fde7ace7`
- Timestamp normalization: `America/Los_Angeles` at MT5 export time to UTC,
  then explicitly to `America/New_York` for the strategy session.
- Results use normalized R only. No position size, account value, leverage, or
  dollar P&L was assumed.
- Scheduled news/event policy was intentionally **not** applied. It is a
  separate Risk Engine control and combining it with this hypothesis would
  prevent attribution of the result.

## Coverage

| Item | Count |
| --- | ---: |
| Weekday sessions identified | 781 |
| Incomplete 08:20–13:30 sessions excluded | 25 |
| Stretch warm-up sessions excluded | 10 |
| Sessions evaluated | 746 |
| Neutral or unavailable directional-bias sessions | 162 |
| Sessions with no eligible breakout fill | 123 |
| Completed simulated trades | 460 |
| Ambiguous entry/stop M1 sessions excluded | 1 |
| Forced exits | 186 |
| Protective-stop exits | 274 |
| Positive / negative completed trades | 157 / 303 |

The ambiguous session was 2023-11-24. Its eligible entry and protective stop
were both touched within one M1 bar, so the simulator excluded it rather than
assuming a fill sequence.

## Cost sensitivity

Recorded bar spread is applied throughout. Additional slippage is adverse at
both entry and exit. These are sensitivity scenarios, not asserted live-fill
estimates.

| Scenario | Additional slippage | Total R | Mean R per trade | Positive / negative trades |
| --- | ---: | ---: | ---: | ---: |
| Recorded spread only | 0 points | -15.0663 | -0.0328 | 157 / 303 |
| Plus 1 point | 1 point | -17.6295 | -0.0383 | 157 / 303 |
| Plus 3 points | 3 points | -22.6852 | -0.0493 | 157 / 303 |

## Decision

The experiment exceeds the minimum 100 completed trades but fails the
predeclared research gate: total R and mean R are negative in every cost
scenario, including recorded spread only. The overnight directional filter is
therefore rejected for this venue, dataset, and fixed ORB specification.

The replay is still exploratory because this historical data had already been
viewed for the frozen baseline. That does not weaken the rejection decision;
it prevents any positive result from being treated as independent confirmation.

Do not add a threshold, VWAP, volume, gap, news, or other filter to rescue this
result. Any future idea must begin as a separately documented hypothesis with
a new approval gate.
