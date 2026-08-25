# Crabel Early-Session Directional Breakout — Candidate 003

## Status and identity

**Candidate ID:** `crabel_early_session_directional_breakout_candidate_003`  
**Version:** `0.1-draft-for-data-source-approval`  
**Status:** Draft only. It is the active research track for feasibility work,
but is **not frozen** and authorizes neither raw-data inspection, replay, paper
trading, MT5 integration, nor broker execution.

Candidate 001 (Headway / `XAUUSD`) and Candidate 002 (Exness-MT5Trial9 /
`XAUUSDm`) are separate frozen records. Their datasets, manifests, results,
rules, and approvals must not be used by this candidate.

## Venue scope and hypothesis

**Proposed venue/instrument:** Dukascopy Bank SA, `Dukascopy-demo-mt5-1`, MT5
Demo Account — Hedge, `XAUUSD` only.

The hypothesis is venue-specific: a non-neutral bid-price movement during the
first five completed New York M1 bars after 08:20 predicts same-direction
movement after 08:25 sufficiently to survive recorded spread and fixed adverse
slippage. It makes no claim of performance and inherits no result from another
candidate.

The current source facts are recorded separately in
[`CANDIDATE_003_DUKASCOPY_DATA_SOURCE_ASSESSMENT.md`](CANDIDATE_003_DUKASCOPY_DATA_SOURCE_ASSESSMENT.md).
This draft becomes eligible to freeze only when that assessment records a PASS
for the required source fields and data-separation feasibility.

## Proposed fixed market, signal, and exits

| Item | Definition |
| --- | --- |
| Timezone/session | `America/New_York`; New York weekdays; DST conversion explicit. |
| Observation window | 08:20:00 inclusive through 08:25:00 exclusive: five completed M1 bars. |
| Direction | Compare the 08:20 bid open with the 08:24 bid close: higher is long, lower is short, equality is no trade. |
| Entry | At the 08:25 M1 open in the signalled direction. |
| Limit | One signal and one completed entry per New York date; no re-entry, averaging, reversal, OCO, or target. |
| Executable sides | Buy entry/short exit use ask (bid plus recorded spread); sell entry/long exit use bid. Apply adverse slippage at every executable event. |
| Buy stop | Lowest bid low of the 08:20–08:24 window. |
| Sell stop | Highest ask high of that window, using each bar's recorded spread. |
| Stop validity | Stop must be strictly on the loss side of executable entry; otherwise no trade/risk rejection. |
| Stop model | Long: trigger at bid low <= stop; fill at lesser of stop and bar bid low. Short: trigger at ask high >= stop; fill at greater of stop and bar ask high. Apply adverse slippage. |
| Forced exit | At the executable side of the 13:30 M1 open. At exactly 13:30, forced exit is terminal and precedes any stop test; do not test that bar's high/low for the stop. |
| Ambiguity | An 08:25 entry bar that also touches its stop is excluded and journaled. No favorable intrabar order is assumed. |

## Proposed data, costs, and research measures

- Require UTC-normalized M1 bid OHLC, per-bar recorded spread, tick volume,
  instrument-volume constraints, source/provenance, export timezone, retrieval
  metadata, SHA-256 checksum, and a separately retained quality report.
- Require every M1 bar from 08:20 through 13:30. Missing, duplicate, malformed,
  crossed, spreadless, stale, or clock-regressed data is an exclusion; nothing
  is inferred or filled.
- Apply recorded spread plus fixed adverse slippage of 0, +1, and +3 Dukascopy
  instrument points at entry and exit. `XAUUSD` has verified three digits; the
  exact point value must be recorded from the source specification in the
  frozen data manifest. No representation is changed by this draft.
- For each completed trade, `R = d × (X − E) / |E − S|`, where `d` is +1 for a
  buy and -1 for a sell, `E` is executable entry, `S` validated stop level, and
  `X` executable exit, all under the same cost scenario. Use decimal arithmetic
  without pre-gate rounding. Research is non-sized: each terminal stop or 13:30
  forced-exit fill supplies one R observation; no-signal, rejected, invalid,
  and ambiguous sessions do not count.

## Proposed validation and contamination controls

- Use the standard chronological protocol v0.1: 20% final contiguous untouched
  holdout; five walk-forward windows of 252 training and 63 validation sessions
  with a 63-session step.
- Require >=709 valid sessions after exclusions and >=100 completed trades in
  every cost scenario. Pass only if every scenario has positive total and mean
  R, positive holdout, and at least two positive walk-forward windows.
- Select, checksum-manifest, and access-control an evaluation dataset and a
  later, separately non-overlapping confirmation dataset before either
  dataset's market-data contents are inspected. Dates must be selected from
  availability/protocol facts only, never price behavior, signal frequency,
  returns, or strategy performance.
- The 08:25 decision uses only completed 08:20–08:24 observations. Later bars,
  revised values, labels, and outcomes are forbidden. A failure freezes this
  version without tuning, inversion, filters, or a performance-based rule
  change. A pass permits independent confirmation only.

## Prohibitions before source approval and freeze

No raw CSV may be opened, parsed, replayed, imported, or structurally checked
under this draft. No `RuntimeStrategy`, paper runner, MT5 EA attachment,
bridge, paper executor, order API, or live trading authority is created.

## Approval checklist

- [ ] Data-source feasibility assessment has passed all required source fields,
      history-depth, timestamp-provenance, and separation gates.
- [ ] Evaluation and later independent confirmation ranges are predeclared and
      non-overlapping before raw-data inspection.
- [ ] Both raw exports are checksum-manifested and owner-read-only under the
      unseen-data intake procedure.
- [ ] Candidate 003 version `0.1` is formally frozen without rule changes.
- [ ] A separate research-approval record authorizes deterministic replay only.
