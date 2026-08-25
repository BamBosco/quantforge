# Candidate 003 — Dukascopy Data-Source Feasibility Assessment

**Candidate:** `crabel_early_session_directional_breakout_candidate_003`

**Candidate version assessed:** `0.1-draft-for-data-source-approval`

**Assessment status:** **PENDING — source is promising, but not approved for
dataset intake or replay.**
**Raw-data handling:** No CSV or other raw market-data export was opened,
parsed, previewed, imported, or structurally assessed for this record.

## Source identity observed in MT5

| Fact | Observation | Status |
| --- | --- | --- |
| Broker | Dukascopy Bank SA | Verified |
| Server | `Dukascopy-demo-mt5-1` | Verified |
| Account | Demo Account — Hedge | Verified |
| Instrument | `XAUUSD` — US Dollar vs Spot Gold | Verified |
| Timeframe | M1 | Verified |
| Chart basis | Bid price | Verified |
| Digits | 3 | Verified |
| Contract size | 100 XAU | Verified |
| Spread | Floating | Verified |
| Volume bounds/step | 0.01 minimum; 10,000 maximum; 0.01 step; 1,000 limit | Verified |
| Trading session | Monday–Friday, 01:00–24:00 (terminal session display) | Verified |
| Execution | Market | Verified |

## Historical availability and export capability

The MT5 Symbols/Bars export dialog displayed an `XAUUSD` M1 export interval
from `2019-08-01 01:05` through `2026-08-20 23:59`. This is evidence that the
terminal can load and offer export of substantial M1 history rather than only
recent chart candles. The native **Export Bars** CSV action was available. A
user-created CSV was reported as saved; it was deliberately not accessed here.

| Question | Finding | Status |
| --- | --- | --- |
| Earliest genuinely retrievable M1 boundary | `2019-08-01 01:05`, as displayed in the MT5 export range | Verified as terminal export boundary |
| Latest genuinely retrievable M1 boundary | `2026-08-20 23:59`, as displayed in the MT5 export range | Verified as terminal export boundary |
| Substantial M1 history loaded | Approximately seven years offered by the export dialog | Verified |
| Native historical export | MT5 Bars → Export Bars → CSV Save As | Verified |
| Timestamp / date field | Bars dialog shows `Date` | Verified |
| Recorded spread field | Bars dialog shows `Spread` | Verified |
| Bid OHLC CSV fields | Not inspected | **UNKNOWN** |
| Ask price / ask-high field | Not inspected | **UNKNOWN** |
| Tick-volume CSV field | Not inspected | **UNKNOWN** |
| CSV timestamp basis / UTC conversion | Terminal/local export timezone was not displayed | **UNKNOWN** |
| 14-day demo impact after expiry | Not displayed or tested | **UNKNOWN** |

## Required fields and source-provenance gate

Candidate 003 cannot proceed to data intake unless the export format is
confirmed, without strategy evaluation, to provide: timestamp; bid OHLC;
per-bar recorded spread sufficient to model executable ask; tick volume;
point/digits; volume constraints; server/account provenance; terminal-local
export timezone; retrieval timestamp; and selected coverage. The last two
timezone facts must support deterministic normalization to UTC before applying
`America/New_York` and its DST rules.

The displayed MT5 session hours do not establish a raw-export timestamp basis.
They must not be substituted for timezone provenance.

## Capacity and separation gate

The verified 2019–2026 M1 availability is more than adequate in calendar span
to *potentially* contain 709 New York weekdays and to divide older evaluation
history from later confirmation history. It does **not** establish 709 complete
08:20–13:30 New York sessions: that requires a later, separately authorized
structural quality check after role-specific exports have been frozen.

| Gate | Finding | Status |
| --- | --- | --- |
| Potential calendar capacity for >=709 sessions | Yes, based on observed multi-year archive span | Potential only |
| >=709 complete qualifying sessions | Raw rows not assessed | **UNKNOWN** |
| Later independent confirmation capacity | Calendar span appears sufficient | Potential only |
| Non-overlap with Candidate 001/002 data | Required by governance; no Candidate 001/002 file is eligible for Candidate 003 | Required control |
| Evaluation/confirmation date selection | Must be predeclared on availability/protocol facts only, not price behavior, signals, returns, or performance | Required control |

## Required governance controls before any inspection

1. Create a Candidate 003 data-selection record with a predeclared evaluation
   range and a later non-overlapping confirmation range, chosen only from the
   verified archive boundaries and chronological protocol needs.
2. Export each range independently into distinct Candidate 003 role
   directories. Do not open, preview, parse, merge, or reuse the existing
   saved CSV.
3. Record the terminal-local timezone, terminal/server identity, symbol,
   timeframe, requested range, and retrieval time; freeze each export with a
   SHA-256 manifest and owner-only access as required by
   [`RESEARCH_DATASET_INTAKE.md`](../../docs/RESEARCH_DATASET_INTAKE.md).
4. Only after a separate authorization may a structural quality report inspect
   the frozen raw rows. It must determine complete-session counts and field
   sufficiency without calculating strategy performance.
5. Replay requires a later independent research-approval record. A passing
   research gate would permit only independent confirmation, never paper or
   live trading.

## Data-source decision

**Decision: PENDING.** Dukascopy passes the preliminary terminal-access,
symbol, M1, multi-year history-depth, and native-export observations. It has
not yet passed the raw-field, timestamp-provenance, complete-session, later
confirmation, or post-expiry demo-access gates. Candidate 003 therefore remains
draft and no research replay is authorized.
