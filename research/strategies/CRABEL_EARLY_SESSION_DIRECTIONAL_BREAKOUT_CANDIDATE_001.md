# Crabel Early-Session Directional Breakout — Candidate 001

## Status and identity

**Candidate ID:** `crabel_early_session_directional_breakout_candidate_001`  
**Version:** `0.2-frozen`  
**Status:** Frozen specification only. No code, replay, data acquisition, or
paper execution is authorized by this document.

## Hypothesis and source fidelity

**Source-supported premise:** the Crabel review states that the first 5–10
minutes may contain directional information relevant to later movement.

**QuantForge-specific design decision:** test exactly the first **five** minutes
of the established New York research session, with no threshold, filter,
indicator, gap, inside-day, prior-day-structure, volatility, or volume input.
The source does not prescribe this executable rule, stop, exit, or venue.

**Hypothesis:** for Headway Demo `XAUUSD`, a non-neutral bid-price movement from
08:20 through 08:24 New York time predicts the same directional movement after
08:25 sufficiently to survive recorded spread and fixed adverse-slippage
stress.

## Market, data, and session

| Item | Frozen definition |
| --- | --- |
| Venue/instrument | Headway Demo `XAUUSD` only; no portability to another broker or symbol is assumed. |
| Timezone/session | `America/New_York`; New York weekdays only; DST conversion is explicit. |
| Observation window | 08:20:00 inclusive through 08:25:00 exclusive: exactly five completed M1 bars. |
| Trade window | Entry at the 08:25 M1 open; protective monitoring until forced exit at the 13:30 M1 open. |
| Price side | Bid OHLC determines movement and long-stop tests. Ask is bid plus recorded spread for buy execution and short-stop tests. |
| Required data | UTC timestamped M1 bid OHLC, per-bar recorded spread, instrument volume constraints, and source/dataset manifest with checksum and timezone provenance. |
| Data quality | Require every M1 bar from 08:20 through 13:30, plus complete prior metadata required by the manifest. Missing, duplicate, malformed, crossed, spreadless, stale, or clock-regressed data produces a recorded no-trade/exclusion. |
| Runtime freshness | At entry, the observation must be timezone-aware, not future-dated, and no more than 30 seconds old. Otherwise emit no signal. |

## Signal, entry, and lifecycle

1. Let `open_0820` be the bid open of 08:20 and `close_0824` the completed bid
   close of 08:24.
2. `close_0824 > open_0820` is bullish; emit one buy-market intent at 08:25.
   `close_0824 < open_0820` is bearish; emit one sell-market intent at 08:25.
   Equality is neutral and emits no signal.
3. There is at most one signal and one completed entry per New York date.
   The idempotency key is candidate ID/version plus New York date; duplicates
   emit no second signal and are journaled.
4. Entry is immediate, not conditional. There is no OCO pair, trigger order,
   averaging, re-entry, reversal, or target order.
5. Buy entry uses the 08:25 ask; sell entry uses the 08:25 bid, with the
   applicable adverse-slippage scenario added in the adverse direction.

## Risk exits and ambiguity

| Item | Frozen definition |
| --- | --- |
| Buy protective stop | Lowest bid low in the 08:20–08:24 observation window. |
| Sell protective stop | Highest ask high in the 08:20–08:24 observation window, where ask high is bid high plus that bar's recorded spread. |
| Stop validity | The stop must be strictly on the loss side of the executable entry; otherwise record a risk rejection/no trade. |
| Target | None. No target, trailing stop, break-even move, scale-out, or discretionary exit. |
| Forced exit | Close any open position at the executable side of the 13:30 M1 open. |
| Stop fill model | A long stop triggers on a later bid low at or below the stop and fills at the lesser of stop and bar bid low; a short stop triggers on a later ask high at or above the stop and fills at the greater of stop and bar ask high. Apply adverse slippage. |
| 13:30 stop/forced-exit precedence | At the exact 13:30 M1 observation, process the scheduled forced exit first and terminally: fill at the executable 13:30 open with its adverse slippage, label `forced_exit`, and do not evaluate that bar's high/low for a protective stop. Protective-stop monitoring applies only to executable observations strictly earlier than 13:30. |
| Ambiguity | If the 08:25 entry bar also touches the protective stop, exclude and journal the session as ambiguous. Any missing/duplicate/spreadless required bar is also an exclusion. No favorable intrabar sequence is assumed. |

## Costs, validation, and promotion

- Apply recorded spread at every executable event and fixed adverse slippage of
  **0, +1, and +3 points** at every entry and exit. All three scenarios use the
  same eligible dates and no-trade/exclusion decisions.
- Use the standard chronological protocol v0.1: 20% untouched holdout; five
  chronological walk-forward windows with 252 training sessions, 63 validation
  sessions, and a 63-session step.
- Require at least **709 valid sessions** after exclusions to support that
  structure and at least **100 completed trades**. Evaluate all three cost
  scenarios.
- For every completed trade, let `d = +1` for a buy and `d = -1` for a sell,
  `E` be the simulated executable entry price after the applicable recorded
  spread and adverse entry slippage, `S` be the validated protective-stop
  price, and `X` be the simulated executable exit price after the applicable
  recorded spread and adverse exit slippage. Its normalized result is exactly
  `R = d × (X − E) / |E − S|`. `S` is the protective-stop level, not a
  hypothetical stop-fill price; therefore gap/slippage beyond the stop can
  produce `R < -1`. This formula is evaluated using exact decimal arithmetic
  and no rounding of R before reporting or gating.
- Research is strictly non-sized: every completed simulated trade contributes
  one normalized-R observation under the formula above, regardless of account
  equity, leverage, lot size, broker volume bounds, or any risk-budget amount.
  A completed trade for the **>=100** gate is only an eligible session with one
  completed entry and one terminal protective-stop or 13:30 forced-exit fill;
  no-signal, rejected, invalid-data, and ambiguous sessions contribute no R
  and do not count. The same completed-trade definition and eligible dates
  apply to each cost scenario.
- This research convention does not authorize a quantity. If the candidate is
  ever considered outside research, only the Risk Engine may size an approved
  intent: `risk_per_lot = |E − S| × value_per_price_unit_per_lot`,
  `risk_budget = current_equity × approved_risk_fraction`, and
  `quantity = min(maximum_volume, floor_to_volume_step(risk_budget /
  risk_per_lot))`; it rejects a quantity below `minimum_volume` and all other
  Risk Engine limit failures. This is a future execution-control convention,
  not an input to research R or the completed-trade gate.
- Research passes only if every scenario has positive total R, positive mean R,
  a positive holdout, and at least two positive walk-forward windows. Otherwise
  freeze this version without tuning, inversion, or filtering.
- A pass permits independent confirmation only. Confirmation must use a
  separate, checksum-recorded, non-overlapping and previously unseen dataset,
  with the identical rules, cost scenarios, session handling, and validation
  gate. It must independently pass before paper approval can be requested.

## No-lookahead and contamination controls

- The 08:25 decision uses only the completed 08:20–08:24 bars and data known
  at 08:25. Later bars, revised values, future event outcomes, and derived
  labels are forbidden.
- The entire evaluation and confirmation datasets must be selected, manifested,
  and access-controlled before their results are inspected. They may not
  overlap the previously viewed Headway datasets ending `2026-08-14T17:53Z`.
- This candidate does not alter, filter, invert, or inherit performance claims
  from the frozen ORB baseline, ORB overnight-bias variant, or Intraday
  Momentum Experiment 001.
- Any rule not stated here is prohibited. A proposed change requires a new
  candidate ID/version, fresh approval, and a new unseen evaluation plan.

## Frozen-specification and research-authorization checklist

- [x] Candidate ID/version and this exact document are frozen as `0.2-frozen`.
- [x] The five-minute window, bid movement definition, entry, stop, no-target,
      13:30 exit, stop/forced-exit precedence, and ambiguity policy are fixed.
- [x] The exact normalized-R formula, non-sized research convention,
      completed-trade definition, and future Risk-Engine-only sizing convention
      are fixed.
- [x] The Headway Demo `XAUUSD` scope and New York/DST calendar are fixed.
- [x] The M1/spread/manifest/freshness/data-quality requirements are fixed.
- [x] The 0/+1/+3-point cost model and adverse fill rules are fixed.
- [x] The 709-session, 100-trade, chronological validation, and failure gates
      are fixed.
- [ ] A non-overlapping, unseen evaluation dataset and a later independent
      confirmation dataset are named, checksum-manifested, and access-controlled
      before inspection.
- [ ] A research approval record authorizes deterministic replay only; it does
      not authorize paper or MT5 execution.
