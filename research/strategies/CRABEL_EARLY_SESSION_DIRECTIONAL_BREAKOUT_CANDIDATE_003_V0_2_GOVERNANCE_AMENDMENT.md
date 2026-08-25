# Crabel Early-Session Directional Breakout — Candidate 003 v0.2

## Formal freeze and research-governance amendment

**Candidate ID:** `crabel_early_session_directional_breakout_candidate_003`

**Supersedes:** Candidate 003 `0.1-draft-for-data-source-approval` for status
and research-governance sequencing only.

**Version:** `0.2-frozen`

**Status:** Frozen strategy specification and governance amendment. It does
not authorize a replay, performance inspection, confirmation inspection, paper
mode, MT5 execution, or live trading.

## Purpose and factual record

Candidate 003's frozen Dukascopy `XAUUSD` evaluation export passed its authorized
structural-quality assessment with 1,010 complete New York 08:20–13:30 sessions
against the unchanged >=709-session minimum. Its SHA-256 matches the immutable
base manifest. No signal, trade, R value, return, or performance result has
been calculated or inspected.

The pre-replay audit identified two governance defects: the strategy was still
labelled draft, and its base manifest lacked point/digits and volume metadata.
It also identified a sequencing deviation: evaluation structural inspection
occurred before a confirmation raw export and manifest existed. This amendment
records and resolves those governance facts without concealing them and without
changing the hypothesis or any trading rule.

## Immutable trading provisions carried forward

Every Candidate 003 v0.1 trading and validation provision is carried forward
unchanged into v0.2:

| Provision | v0.2 status |
| --- | --- |
| Dukascopy Bank SA / `Dukascopy-demo-mt5-1` / `XAUUSD` venue scope | Unchanged |
| Crabel early-session directional hypothesis | Unchanged |
| `America/New_York` session and DST treatment | Unchanged |
| Five completed M1 bars from 08:20–08:24 | Unchanged |
| Positive = long, negative = short, equality = no signal | Unchanged |
| Entry at the 08:25 M1 open; one entry per date | Unchanged |
| Bid/ask executable-side model using recorded spread | Unchanged |
| Buy/sell protective-stop definitions and stop validity | Unchanged |
| Stop trigger/fill model | Unchanged |
| 13:30 forced exit and terminal precedence | Unchanged |
| 08:25 entry-bar/stop ambiguity exclusion | Unchanged |
| Recorded-spread treatment and 0/+1/+3 point adverse-cost scenarios | Unchanged |
| Exact normalized-R formula and decimal treatment | Unchanged |
| Non-sized research convention and completed-trade definition | Unchanged |
| >=709 complete qualifying-session minimum | Unchanged |
| >=100 completed-trade minimum in every cost scenario | Unchanged |
| 20% final contiguous untouched holdout | Unchanged |
| Five chronological 252/63 walk-forward windows with 63-session step | Unchanged |
| No-lookahead, no tuning, no inversion, no filtering, and no optimization controls | Unchanged |
| Failure and promotion gates | Unchanged |

The >=709-session and >=100-completed-trade gates may not be lowered, waived,
averaged across data roles, or met by combining datasets.

## Frozen evaluation manifest bundle

The immutable base manifest remains unchanged:

- raw file: `XAUUSD_M1_201908010105_202308012354.csv`
- base manifest: `dukascopy_demo_mt5_1_xauusd_m1_20190801_20230801.manifest.toml`
- SHA-256: `7942acbdafb1343a8d42032d8048a6f43ecc9b7e8df03fab40908b18dc3635ef`

For v0.2, the base manifest and the immutable
`dukascopy_demo_mt5_1_xauusd_m1_20190801_20230801.instrument_specification_provenance.toml`
form the frozen evaluation manifest bundle. The addendum is bound to the same
raw filename and SHA-256 and records the previously verified MT5 Symbol
Specification: 3 digits, point size 0.001, contract size 100 XAU, floating
spread, bid-price chart mode, market execution, 0.01 minimum volume, 10,000
maximum volume, 0.01 volume step, and 1,000 volume limit.

The addendum is provenance only. It cannot alter the raw CSV, checksum,
timestamps, structural-quality result, evaluation role, or any Candidate 003
rule.

## Sequencing deviation and amended confirmation procedure

The v0.1 draft required the confirmation raw export to be checksum-manifested
and access-controlled before *either* dataset was inspected. That did not
occur: the named evaluation file was structurally inspected before a
confirmation export existed. This historical deviation is permanent and must
not be represented as compliance with the v0.1 sequence.

The evaluation dataset is permanently identified as inspected **evaluation
evidence**. It cannot be replaced, relabelled as unseen, merged, supplemented,
or used to choose or change a rule. No performance evidence exists in it.

The v0.2 procedure is:

1. Keep the evaluation raw file, base manifest, manifest-provenance addendum,
   and quality report immutable and role-separated.
2. Before any evaluation replay authorization, separately export the
   predeclared later confirmation period; create its own SHA-256 manifest and
   restricted access control from raw bytes only. This is an acquisition/freeze
   action, not confirmation inspection.
3. Do not open, preview, parse, quality-assess, replay, or derive any result
   from confirmation data until the authorized evaluation replay has passed all
   unchanged gates.
4. Preserve chronological non-overlap: confirmation remains later than
   evaluation and cannot be reassigned as evaluation evidence.
5. After an evaluation pass, issue a separate confirmation-inspection and
   confirmation-replay authorization. An evaluation pass permits only that
   independent confirmation study, never paper or live trading.

This amendment changes the sequencing governance only; it does not lessen
independence, no-lookahead, contamination, session-completeness, or promotion
requirements.

## Authorization state

- [x] Candidate 003 v0.2 strategy specification formally frozen.
- [x] Evaluation raw file, base manifest, and structural-quality report retained.
- [x] Evaluation manifest-provenance addendum frozen and bound to the unchanged SHA-256.
- [x] Evaluation structural gate: 1,010 complete sessions >=709.
- [ ] Later confirmation raw export separately frozen, checksummed, and access-controlled.
- [ ] Evaluation replay authorization.
- [ ] Evaluation replay.
- [ ] Confirmation inspection and replay after evaluation pass.
- [ ] Paper approval.
- [ ] Live approval.

## Non-authorization statement

This amendment grants no deterministic replay authorization yet. It does not
authorize performance inspection, optimization, tuning, inversion, filtering,
confirmation access, paper mode, MT5 execution, a broker order, or live
trading.
