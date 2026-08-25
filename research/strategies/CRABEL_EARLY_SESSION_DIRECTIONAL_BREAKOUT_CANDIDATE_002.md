# Crabel Early-Session Directional Breakout — Candidate 002

## Status and identity

**Candidate ID:** `crabel_early_session_directional_breakout_candidate_002`  
**Version:** `0.1-frozen`  
**Status:** Frozen specification only. It does not authorize data inspection,
replay, paper trading, MT5 integration, or execution.

## Scope and hypothesis

This is a new, venue-specific candidate. It has no performance claim, data,
result, or authorization from Candidate 001. Candidate 001 remains frozen and
untested for Headway Demo only.

**Venue/instrument:** Exness `Exness-MT5Trial9` demo server, `XAUUSDm` only.
The server identity, exact symbol spelling, account environment, instrument
specification, and terminal-local export timezone must be recorded in each
dataset manifest. No portability to Headway, MetaQuotes-Demo, another Exness
server/account type, or another gold symbol is assumed.

**Hypothesis:** for Exness `XAUUSDm`, a non-neutral bid-price movement from
08:20 through 08:24 New York time predicts same-direction movement after 08:25
sufficiently to survive recorded spread and fixed adverse-slippage stress.

## Fixed market, signal, and exits

| Item | Definition |
| --- | --- |
| Timezone/session | `America/New_York`; New York weekdays; DST conversion explicit. |
| Observation window | 08:20:00 inclusive through 08:25:00 exclusive: five completed M1 bars. |
| Entry | At the 08:25 M1 open: buy when 08:24 bid close exceeds 08:20 bid open; sell when it is below; equality is no trade. |
| Limit | One signal and one completed entry per New York date; no re-entry, averaging, reversal, OCO, or target. |
| Executable sides | Buy entry/short exit use ask (bid plus recorded spread); sell entry/long exit use bid. Apply adverse slippage at every executable event. |
| Buy stop | Lowest bid low of the 08:20–08:24 window. |
| Sell stop | Highest ask high of that window, using each bar's recorded spread. |
| Stop validity | Stop must be strictly on the loss side of executable entry; otherwise no trade/risk rejection. |
| Stop model | Long: trigger at bid low <= stop; fill at lesser of stop and bar bid low. Short: trigger at ask high >= stop; fill at greater of stop and bar ask high. Apply adverse slippage. |
| Forced exit | At the executable side of the 13:30 M1 open. At exactly 13:30, forced exit is terminal and precedes any stop test; do not test that bar's high/low for the stop. |
| Ambiguity | An 08:25 entry bar that also touches its stop is excluded and journaled. No favorable intrabar order is assumed. |

## Data, costs, and research measures

- Require UTC-normalized M1 bid OHLC, per-bar recorded spread, tick volume,
  instrument-volume constraints, source/provenance, export timezone, retrieval
  metadata, SHA-256 checksum, and a separately retained quality report.
- Require every M1 bar from 08:20 through 13:30. Missing, duplicate, malformed,
  crossed, spreadless, stale, or clock-regressed data is an exclusion; nothing
  is inferred or filled.
- Apply recorded spread plus fixed adverse slippage of 0, +1, and +3 instrument
  points at entry and exit. The Exness point size and volume constraints must be
  captured from the Exness symbol specification before replay; they are not
  guessed from another venue.
- For each completed trade, `R = d × (X − E) / |E − S|`, where `d` is +1 for a
  buy and -1 for a sell, `E` is executable entry, `S` validated stop level, and
  `X` executable exit, all under the same cost scenario. Use decimal arithmetic
  without pre-gate rounding. Research is non-sized: each terminal stop or 13:30
  forced-exit fill supplies one R observation; no-signal, rejected, invalid,
  and ambiguous sessions do not count.
- Future execution, if ever separately authorized, remains Risk-Engine-only:
  `risk_per_lot = |E − S| × value_per_price_unit_per_lot`; size from approved
  current-equity risk budget, rounded down to Exness volume step and subject to
  its recorded volume bounds and all existing Risk Engine limits.

## Validation and contamination controls

- Use the standard chronological protocol v0.1: 20% final untouched holdout;
  five walk-forward windows of 252 training and 63 validation sessions with a
  63-session step.
- Require >=709 valid sessions after exclusions and >=100 completed trades in
  every cost scenario. Pass only if every scenario has positive total and mean
  R, positive holdout, and at least two positive walk-forward windows.
- Select, checksum-manifest, and access-control the Exness evaluation dataset
  and a later, separately non-overlapping Exness confirmation dataset before
  either dataset's market-data contents are inspected. The raw exports may not
  be appended, merged, replaced, or used to choose rules.
- The 08:25 decision uses only completed 08:20–08:24 observations. Later bars,
  revised values, labels, and outcomes are forbidden. A failure freezes this
  version without tuning, inversion, filters, or a performance-based rule
  change. A pass permits independent confirmation only.

## Approval checklist

- [x] Candidate ID/version and complete venue scope are approved and frozen as
      `0.1-frozen`.
- [x] Signal, entry, stops, 13:30 precedence, ambiguity, normalized R, and
      non-sized research convention are accepted without amendment.
- [ ] Exness `XAUUSDm` point size, volume constraints, source timezone, and
      export provenance are recorded without inspecting the export's rows.
- [x] The 0/+1/+3-point cost model and 709-session/100-trade protocol are
      approved without amendment.
- [ ] Separate unseen evaluation and confirmation exports are named,
      checksum-manifested, access-controlled, and non-overlapping before
      market-data inspection.
- [ ] A research approval record authorizes deterministic replay only after the
      preceding items are complete; it never authorizes paper or MT5 execution.
