# QUANTFORGE MASTER CONTEXT

> Canonical handoff/context document for continuing QuantForge across chats and tools.
> Read this before making architectural or policy decisions. Update it when the project state materially changes.

## 1. Project identity

**Project:** QuantForge
**Repository:** `BamBosco/quantforge`
**Primary purpose:** build a disciplined, auditable, fail-closed algorithmic trading research and execution system, currently centered on MT5 read-only observation, XAUUSD Candidate 006, research, paper trading, simulated execution, reconciliation, and eventual broker-specific authorization.

**Owner/decision-maker:** the user. QuantForge is the user's project. The assistant/Codex are engineering/research partners and tools, not the owner and not the authority to command the user.

## 2. Working philosophy

- Be proactive. Do not merely process the user's ideas. Identify missing information, propose useful next actions, research external facts when needed, and surface opportunities to advance the project.
- Do not turn engineering caution into needless paralysis. If a task can be safely attempted, attempt it and report the actual result.
- Do not fabricate evidence, signals, fills, broker facts, or policy validation.
- Do not silently weaken authentication, audit integrity, provenance, or data separation.
- Distinguish three things clearly: research evidence, non-live/paper capability, and production broker execution authority.
- Human decision-making is allowed to accept imperfection and iterate. The system should remain fail-closed where a real-money safety invariant is involved, but research and simulation should progress rather than waiting unnecessarily for perfect information.
- Do not repeatedly revisit completed work without a concrete reason.

## 3. Current architecture

### External project reuse boundary

QuantForge remains the authoritative system for MT5 evidence, XAUUSD policy,
risk decisions, paper trading, simulation, reconciliation, and audit. External
projects are references or optional research inputs, not replacement execution
engines:

- **Freqtrade**: reference its backtesting, dry-run, strategy-isolation, and
  reporting practices. Its crypto exchange adapters are not used for MT5
  XAUUSD execution.
- **TradingAgents**: optional research/advisory layer for market-context
  hypotheses. Its output may be stored as analyst evidence, but it cannot
  approve orders, alter risk limits, or bypass the QuantForge risk gate.
- **Superalgos**: optional future visualization and data-pipeline reference.
  Do not introduce its large platform into Candidate 006 while core broker
  evidence remains incomplete.
- **ccxt/binance-trade-bot**: educational Binance-specific reference only; it
  is not a Candidate 006 dependency and is not approved for deployment.

This boundary prevents external frameworks from mixing broker-specific
provenance, weakening the read-only/production authorization boundary, or
creating a second source of truth.

An external XAUUSD repository review is recorded in
`research/results/EXTERNAL_XAUUSD_REPOSITORY_REVIEW_2026-08-27.md`. It found
reusable research patterns, but no external strategy or claimed performance
that is suitable for direct deployment or policy promotion.

A broader 26-repository GitHub survey is recorded in
`research/results/GITHUB_TRADING_REPOSITORY_SURVEY_2026-08-27.md`. Its fixed
decision is to borrow isolated research and testing patterns only; no turnkey
EA, grid logic, fixed-pip policy, claimed win rate, or live connector becomes a
second QuantForge source of truth.

### MT5 read-only observation

Two independent local bridge paths are currently used:

**Dukascopy**
- Bridge: `127.0.0.1:8765`
- Existing XAUUSD read-only observation path

**AssexMarkets**
- Broker server: `AssexmarketsGlobal-Trade`
- Bridge: `127.0.0.1:8766`
- XAUUSD M1
- Dedicated database: `data/candidate_006_second_broker/mt5_observations.sqlite3`
- Dedicated audit DB: `data/candidate_006_second_broker/xauusd_audit.sqlite3`

**AssexMarkets EURUSD clock evidence**
- Bridge: `127.0.0.1:8767`
- Separate database: `data/assexmarkets_eurusd/mt5_observations.sqlite3`
- Scope: read-only EURUSD M1 broker-infrastructure clock/session evidence only
- No Candidate 006 audit consumer and no policy transfer to XAUUSD
- Receiver prepared and health-checked on 2026-08-27. The attached
  non-submitting EA has produced 200 accepted authenticated EURUSD receipts,
  all with complete provenance, through 2026-08-27T11:08:42Z. Twenty-three
  preserved XAUUSD receipts in that database are excluded from EURUSD analysis
  and retained as contamination evidence.
  The 23 records span 09:22:53Z–10:41:01Z and have no payload-hash overlap
  with the dedicated XAUUSD database, proving temporary EA endpoint
  misconfiguration rather than database duplication. The bridge now supports
  an optional `--expected-symbol` receiver guard for future process launches.
- The EA is scalar by design (`SymbolToReport` plus one `BridgeUrl`), so
  simultaneous EURUSD/XAUUSD collection requires two charts and two EA
  instances. This preserves exclusive routing and does not weaken the
  read-only boundary.
- The dedicated XAUUSD receiver recovered and reached 735 accepted receipts
 through 2026-08-27T11:08:48Z, adding forty fresh authenticated receipts with
 current UTC+3 provenance. The parallel-terminal period also placed 23
  XAUUSD receipts in the EURUSD database; they remain excluded and do not
  weaken the dedicated XAUUSD evidence isolation.

- Historical-boundary analysis of the frozen 1,629,646-row export found 1,191
  source dates: 1,173 (98.5%) start at 01:00, with 1,197 gaps over 30 minutes
  and 18 delayed/shifted opens. The recurring daily gap and delayed Friday
  opens are historical observations, not authoritative session or holiday
  rules. See `research/results/CANDIDATE_006_ASSEXMARKETS_HISTORICAL_BOUNDARIES_2026-08-27.md`.
  A thresholded scan also identifies 77 dates ending before 23:30 source time,
  many aligned with recognizable US holiday dates; these remain holiday/early-
  close candidates rather than a broker calendar.

- HFM evaluation is a separate research path; AssexMarkets evidence and
  Candidate 006 are unchanged. HFM public sources confirm MT5 for Forex and
  Metals and publish GMT+2 winter/GMT+3 summer server time, but not exact
  symbol-level sessions, holidays, margin tiers, or EA permissions. Screenshots
  supplied on 2026-08-27 directly show an HFMMarketsGlobal-Demo Demo Premium
  MT5 account (displayed leverage 1:1000), XAUUSD contract size 100 with
  0.01/0.01/100 volume bounds and USD currencies, and EURUSD contract size
  100,000 EUR with 0.01/0.01/500 volume bounds and displayed notional margin
  tiers of 1x/2x/3x. These are account/server-specific MT5 observations pending
  authenticated read-only receipts, not broker-authoritative policy changes.

AssexMarkets must remain separated from the old 8765 log. After the MT5 account switch, the old 8765 database received AssexMarkets receipts and is considered contaminated for post-switch cross-broker comparison. Do not use it as clean AssexMarkets evidence.

### Candidate 006

Candidate 006 is the XAUUSD profile. Its non-live path includes:

`observation -> validation -> readiness -> strategy -> paper order -> simulated fill -> position state -> reconciliation -> audit`

The non-live artifacts retain the safety boundary around real execution. Historical replay has already verified the complete paper/simulation lifecycle using frozen XAUUSD M1 data.

### Execution boundary

The system has read-only MT5 observation, paper trading, simulated fills, position-state tracking, reconciliation, and audit infrastructure.

**Actual broker order submission remains disabled/not authorized.** Production execution must be treated as a separate authorization decision after broker-specific evidence and review.

## 4. Confirmed completed capabilities

- MT5 read-only bridge
- USDJPY observation
- XAUUSD live observation
- authenticated local bridge
- position-state observer
- broker receipt reconciler
- audit architecture
- Qwen3 five-role path
- 90-second freshness protection
- timestamp protection
- protective-level validation
- daily equity baseline
- Candidate 006 XAUUSD profile
- XAUUSD broker metadata observation
- XAUUSD risk calculation
- provisional/non-live Stage A constructor
- non-live readiness
- paper trading runtime
- historical simulated fills
- position-state lifecycle
- paper receipt reconciliation
- resilient live paper monitoring
- Candidate 006 non-live checks included in CI

Latest known pre-handoff full verification milestone: 242 tests passed, Ruff passed, strict Mypy passed. Do not claim this as a fresh validation after later changes unless a new run confirms it.

## 5. Candidate 006 policy state

### Spread

Dukascopy evidence previously established a 99.5th-percentile session spread around 760 raw MT5 points.

AssexMarkets historical M1 evidence now shows:
- median: 8 points
- P95: 19
- P99: 30
- P99.5: 30
- P99.9: 50
- maximum: 358

A broker-specific AssexMarkets research cap around 30 raw MT5 points is now materially supported by the historical dataset, but it is not a universal XAUUSD rule and must not overwrite Dukascopy evidence.

### Risk / maximum position

Still provisional. Historical bars do not establish account equity, leverage, margin behavior, stop/freeze constraints, realized execution loss, or a promoted directional strategy's approved risk budget.

### Session

🟡 Partially established. Fresh EA 1.01 receipts from
`AssexmarketsGlobal-Trade` measured MT5 server time as UTC+3 on 2026-08-26,
terminal-local time as UTC+1, and the terminal UTC clock as exact. This proves
the current server offset, but not the January-August export's winter offset or
the broker's DST rule. Historical source-clock hours remain provisional until
a DST-boundary receipt or broker-authoritative confirmation is captured.
EURUSD now provides 52/52 current UTC+3 receipts, but its twenty-seven-minute
observation window contains no weekly close/open, daily break, rollover, or
DST boundary.

The larger 2022–2026 native export structurally aligns predominantly with
UTC+3: 235 of 241 weekly first bars are Monday 01:00 source clock. However, it
contains a one-week 00:00–22:58 reversal from 2025-10-27 through 2025-10-31,
then returns to the normal 01:00–23:58 span. This is useful DST-adjacent
research evidence, not authority to normalize timestamps or promote a session
policy.

Quantitative source-boundary scoring favors fixed UTC+3 (1,173/1,191 daily
first bars, 98.5%; 240/241 weekly first bars, 99.6%) over fixed UTC+2 (1.4% /
0.4%), Europe-style UTC+2/+3 (59.4% / 59.3%), and US-style UTC+2/+3 (65.7% /
65.6%). The 2025 anomaly is temporally between Europe and US DST end dates but
does not recur in the equivalent 2022–2024 windows. A spring 2025 close-only
change is also incompatible with a simple seasonal conversion. Keep the UTC
freeze blocked pending broker confirmation of historical server/export time.

### Execution deviation

🟡 Partially evidenced. One user-authorized AssexMarkets demo round trip was
completed: XAUUSD BUY 0.01 opened at 4593.51 at server time 23:49:59, then
closed at 4592.61 at 23:53:43, with realized P/L of -0.90 USD. MT5 history
showed tickets 29455831 (position), 29196312 (entry), and 29196594 (exit);
the post-close receipt showed zero positions and zero margin. This proves one
broker fill/close outcome, but not latency, request price, retcode, or a
statistically useful slippage distribution.

## 6. AssexMarkets historical dataset

Raw filename:
`XAUUSD_M1_202601020100_202608141159.csv`

Raw size:
`13,357,126 bytes`

SHA-256:
`45a24b5f53c5518f73a310800705ef0ce26036a8a315ee97c80073fb4bf85f33`

Observed source-clock coverage:
`2026-01-02 01:00:00` through `2026-08-14 11:59:00`

Rows: `217,842`

Validation:
- duplicate timestamps: 0
- timestamp regressions: 0
- invalid OHLC rows: 0
- null/empty fields: 0
- negative/non-positive tick volume: 0
- negative spreads: 0
- zero-spread rows: 8

Observed weekday dates: 160.

Against the recurring observed source-clock weekday schedule, 2,798 M1 bars are missing. The dataset is useful but not perfectly continuous.

`<VOL>` is zero throughout and is not treated as traded-volume evidence.

For source-clock 08:20-13:30, 157 of 160 dates are complete. Do not convert that window to America/New_York until timezone provenance is established.

### Local evidence artifacts

The current ChatGPT runtime has copies under:
- `/mnt/data/candidate_006_assexmarkets_evidence/ASSEXMARKETS_XAUUSD_M1_HISTORICAL_REVIEW_2026-08-26.md`
- `/mnt/data/candidate_006_assexmarkets_evidence/historical_raw/XAUUSD_M1_202601020100_202608141159.csv`
- `/mnt/data/candidate_006_assexmarkets_evidence/historical_raw/manifest.json`
- `/mnt/data/candidate_006_assexmarkets_evidence/historical_raw/quality_metrics.json`

The original Mac source is under the MT5 Wine prefix, then copied into the project raw directory:
`data/candidate_006_second_broker/raw/XAUUSD_M1_202601020100_202608141159.csv`

Do not modify the raw CSV.

### Full-history source-clock dataset

The additional full export is frozen at:
`data/candidate_006_second_broker/raw/XAUUSD_M1_202201030100_202608141159.csv`

- 1,629,646 valid rows, source-clock 2022-01-03 01:00 through 2026-08-14 11:59
- SHA-256 `22d471a693a204c227cfa53ed8798ca983d2699b075e26cc877dcaed2bf35875`
- structural validation found no duplicate, malformed, invalid-OHLC,
  negative-tick-volume, or negative-spread rows
- no UTC-normalized derivative is authorized; see
  `research/results/CANDIDATE_006_ASSEXMARKETS_FULL_HISTORY_SOURCE_CLOCK_2026-08-27.md`

## 7. AssexMarkets broker evidence still needed

1. Winter/DST-boundary evidence tying the historical export clock to the
   current MT5 server-time provenance.
2. Authoritative XAUUSD point size/digits/contract specification if conversions beyond raw MT5 spread points are required.
3. Broker-authoritative XAUUSD trading hours.
4. Holiday and rollover rules.
5. Margin and volume rules.
6. Continued independent `:8766` live receipt collection across normal/stressed/rollover/news conditions.
7. Additional independent execution-quality evidence if deviation policy is
   ever to be promoted: request time, quote, fill, latency, slippage/adverse
   movement, rejection/retcode, reconciliation. One demo round trip is now
   recorded, including broker fill prices and post-close reconciliation.
8. Proper UTC-normalized evidence freeze once the DST/export relationship is
   authoritative.

## 8. Existing AssexMarkets observed contract facts

From live read-only receipts already reported:
- point/tick size: 0.01
- tick value: $1
- minimum volume: 0.01
- volume step: 0.01
- maximum volume: 100
- contract size: 100
- profit/margin currency: USD
- filling modes: FOK/IOC/BOC

Treat these as broker-observed facts tied to the relevant receipts, not universal assumptions.

### Current live receipt coverage

The dedicated AssexMarkets observation database currently contains 473 accepted
receipts spanning 2026-08-26T13:30:08Z through 2026-08-27T03:49:33Z. 194
receipts include the EA 1.01 `time_provenance` object; they establish the
current server clock at UTC+3, terminal-local clock at UTC+1, and terminal UTC
clock exact (apart from ordinary sub-minute capture skew). This is ongoing
observation coverage, not execution-quality evidence. It does not establish
the historical export's timestamp basis or its winter/DST relationship.

### Cross-instrument clock corroboration (2026-08-27)

The isolated EURUSD receiver at `127.0.0.1:8767` is live and writes only to
`data/assexmarkets_eurusd/mt5_observations.sqlite3`. At the analysis point it
contained 19 accepted EURUSD receipts, all with complete time provenance and
an exact MT5 server-minus-UTC offset of +180 minutes. The XAUUSD receiver at
`:8766` contained 695 accepted receipts, 416 with provenance; 388/416 are
within one minute of +180 minutes. Both streams name
`AssexmarketsGlobal-Trade` and therefore corroborate the current **MT5 UTC+3**
clock across two instruments.

This does not resolve the historical XAUUSD export/DST convention. The public
forex page labels its schedule "server time (GMT+0)," which conflicts with the
direct current MT5 receipt data. Do not reinterpret either source silently or
apply the FX schedule to XAUUSD. See
`research/results/CANDIDATE_006_ASSEXMARKETS_CROSS_INSTRUMENT_CLOCK_2026-08-27.md`.

### Demo execution evidence

The first controlled demo execution was performed manually in MT5 on the
AssexMarkets demo account. The position was opened and closed at the minimum
observed volume of 0.01 lots. The screenshot-provided MT5 History record is
the source for the ticket, price, server-time, and realized-P/L facts above;
the bridge independently observed the account flat afterward with balance and
equity at 19,999.10 USD. No production or live-capital execution occurred.

## 9. AssexMarkets external documentation note

Public AssexMarkets material consulted during the handoff indicates XAU/USD is available through MT5 and that metal margin can be tiered by position size. Public forex material states GMT+0 for its forex trading-hours table and 21:00 GMT+0 forex swaps, but it does not bind either statement to XAUUSD metals or to the historical export. Do not use it as a substitute for export/server provenance.

The broker's published terms prohibit automated bots, scripts, and EAs that submit orders without direct manual intervention. This matters for eventual production authorization with AssexMarkets: it is an external constraint as well as QuantForge's own disabled execution boundary. It does not affect the current read-only collection path.

## 10. Historical replay / paper state

Historical replay previously verified:
`historical observation -> genuine 09:00 New York strategy signal -> risk approval -> paper order -> simulated fill -> target exit -> flat simulated position -> reconciliation`

It produced `filled` then `target_reached`, zero final positions, and successful reconciliation. This is historical evidence, not live trading.

Live paper monitoring is designed to process a genuine live signal only when one naturally occurs. A missed 09:00 window must not be recreated after an outage.

## 11. Important past integration history

- Candidate 006 hardening was integrated into `codex/integrate-preserved-development` at `c42d74e`.
- PR #2 was merged into `main` at merge commit `0585a1d0714b489c04098d44a2429e8c923c2dcf`.
- Evidence collection branch: `codex/xauusd-evidence-collection`.
- Relevant later milestones included evidence collection, replication, provisional Stage A, non-live readiness, UTC freshness handling, and second-broker bridge separation.

Do not assume any branch is current without checking Git status/ref.

## 12. Current repository branch state at this handoff

The AssexMarkets historical evidence work added:
- `research/results/CANDIDATE_006_ASSEXMARKETS_XAUUSD_M1_HISTORICAL_EVIDENCE_2026-08-26.md`
- `research/results/CANDIDATE_006_ASSEXMARKETS_XAUUSD_M1_PROVENANCE_2026-08-26.json`

The active evidence branch is `codex/xauusd-evidence-collection`, pushed through
commit `9f8ea9c`. Check the remote before making merge or PR claims.

Fresh verification at `9f8ea9c`: 247 pytest tests passed, Ruff passed, and
strict Mypy passed for production `src`.

## 13. Immediate next work

### Stable completion rubric

Do not recompute one overall percentage when a new evidence requirement is
discovered. Report these fixed dimensions instead:

| Dimension | Current state |
| --- | --- |
| Research infrastructure | Complete |
| Historical replay | Complete |
| Paper/simulation lifecycle | Complete |
| Read-only broker observation | Complete |
| Broker-specific session/timezone evidence | Incomplete |
| Execution-quality distribution | Incomplete |
| Production authorization | Not started; intentionally blocked |

This rubric separates completed engineering from unresolved external broker
facts and prevents progress reports from appearing to regress when scope is
clarified.

Highest-value sequence:

1. Keep both read-only observation paths healthy, especially AssexMarkets `:8766`
   and isolated EURUSD `:8767`; use EURUSD to compare published forex
   server-time claims with current MT5 clocks.
2. Establish AssexMarkets timezone/DST and XAUUSD trading-hours provenance.
3. Verify contract/margin/volume documentation against live observed facts.
4. Freeze the historical dataset through the normal UTC workflow once timezone is authoritative.
5. Recalculate session-aligned spread evidence.
6. Determine whether the Assex-specific spread policy can move from research-only to reviewed policy.
7. Continue live receipt collection.
8. Build independent non-live execution-quality evidence if needed, without real orders unless separately authorized.
9. Run full pytest, Ruff, strict Mypy from the actual checkout after all repository changes.
10. Review and merge PR #3 only after verification.
11. Keep production order submission disabled until the owner explicitly authorizes the production transition after all required broker evidence/review.

## 14. How a new chat should begin

A new chat should treat this document as the project baseline, then inspect the current GitHub branch/main state and any newer commits before making claims about current status.

Suggested opening instruction:

> "Load `docs/QUANTFORGE_MASTER_CONTEXT.md` from the QuantForge repository first. Treat it as the durable project handoff. Then inspect the latest branch/main state, recent commits, open PRs, and current evidence before deciding what to do next. Be proactive and act as an engineering/research partner, not merely a processor of my ideas."

## 15. Non-negotiable distinctions

**Read-only observation is not execution.**

**Historical replay is not live trading.**

**Paper fills are not broker fills.**

**Broker metadata is not a risk policy.**

**Historical spread statistics are not execution-deviation evidence.**

**A provisional policy is not production authorization.**

**A clean test suite is not evidence that the external broker will behave a certain way.**

These distinctions should remain explicit in every future QuantForge handoff.
