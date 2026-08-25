# Candidate 003 v0.2 — Stop-Fill Implementation-Correction Governance Amendment

## Identity, purpose, and status

**Candidate ID:** `crabel_early_session_directional_breakout_candidate_003`  
**Strategy version:** `0.2-frozen`  
**Amendment type:** implementation correction only; not a strategy change and
not Candidate 003 v0.3.

This amendment records a confirmed discrepancy between the frozen Candidate 003
v0.2 stop-fill rule and its replay implementation. It authorizes no replay,
confirmation access, paper mode, MT5 execution, broker execution, or live
trading.

## Unchanged frozen strategy and governance provisions

The following remain exactly unchanged: Candidate ID and v0.2 strategy identity;
Crabel trading hypothesis; five completed 08:20–08:24 `America/New_York` bars;
08:25 entry; directional rules; protective-stop definitions; 13:30 forced exit;
entry-bar ambiguity handling; recorded-spread model; 0/+1/+3 point costs;
normalized-R formula; non-sized convention; >=709 qualifying-session and >=100
completed-trade requirements; 20% final contiguous holdout; five 252/63
walk-forward windows with 63-session step; no-lookahead controls; and all
research failure/promotion gates.

The frozen evaluation dataset remains
`XAUUSD_M1_201908010105_202308012354.csv`, SHA-256
`7942acbdafb1343a8d42032d8048a6f43ecc9b7e8df03fab40908b18dc3635ef`, with
its unchanged evaluation manifest and instrument-provenance addendum. The later
confirmation dataset remains frozen, role-separated, checksum-manifested, and
completely untouched: no inspection, parsing, preview, replay, or result
derivation is authorized by this amendment.

## Confirmed implementation discrepancy

The frozen rule requires:

- Long protective stop: trigger at bid low <= stop; fill at the lesser of stop
  and the triggering bar's bid low, then apply adverse slippage.
- Short protective stop: trigger at ask high >= stop; fill at the greater of
  stop and the triggering bar's ask high, then apply adverse slippage.

The prior implementation correctly tested the bid low / ask high triggers but
incorrectly filled a long with `min(stop, bar.open) - slippage` and a short with
`max(stop, ask_open) + slippage`. Those expressions are replaced only with the
frozen-rule equivalents:

- Long: `min(stop, triggering_bar_bid_low) - adverse_slippage`
- Short: `max(stop, triggering_bar_ask_high) + adverse_slippage`

No other replay, signal, entry, exit, cost, validation, dataset, or rule logic
may change under this correction.

## Evaluation-record status and required sequencing

The existing failed result artifact,
`research/results/candidate_003_v0_2_evaluation_replay.json`, is preserved as
an immutable audit record but is **technically superseded for frozen-rule
conformance purposes** because its stop-fill R values used the incorrect
expressions. It must not be represented as a valid performance test of the
frozen specification.

After the correction is independently tested and its exact source hashes are
recorded, a new separate authorization must bind the unchanged evaluation bundle
and corrected implementation before exactly one deterministic evaluation replay
may occur. This amendment does not itself authorize that replay. It neither
permits confirmation analysis nor changes the frozen failure/promotion sequence.
