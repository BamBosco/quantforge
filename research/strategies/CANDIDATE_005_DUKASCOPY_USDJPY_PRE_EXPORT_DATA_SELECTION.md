# Candidate 005 — Dukascopy USD/JPY Pre-Export / Data-Selection Record

**Candidate ID:** `candidate_005`  
**Stage:** pre-export data selection only  
**Status:** **PENDING — no export is authorized by this record.**

This record does not create or amend a strategy, choose strategy parameters,
inspect market data, establish data quality, calculate sessions, authorize a
replay, or create a confirmation dataset. It records only the intended
role-separated acquisition design for a future, separately authorized
operation.

## Identity and time basis

| Item | Value | Status |
| --- | --- | --- |
| Candidate | `candidate_005` | VERIFIED |
| Instrument | `USD/JPY` / `USDJPY` | VERIFIED |
| Provider | Dukascopy Bank SA historical-data service | VERIFIED |
| Acquisition timestamp basis | GMT / UTC only | PROPOSED — mandatory condition of any future export |
| Future research-time conversion | `UTC timestamp -> America/New_York` via the IANA timezone database | PROPOSED — deterministic only if the acquired file is explicitly GMT/UTC |
| USD/JPY M1 earliest published boundary | `2003-05-04 21:00:00 UTC` (BID M1) | VERIFIED |
| Current/latest USD/JPY M1 archive boundary | `UNKNOWN` | PENDING — must be observed as non-row source metadata immediately before range freezing |

The provider allows historical-data output in GMT or local time. Candidate 005
must explicitly select GMT. No local-time export, terminal-local conversion, or
broker-time assumption is permitted.

## Proposed role-separated ranges

| Dataset role | Range | Status | Control |
| --- | --- | --- |
| Evaluation | `2019-08-01 00:00:00 UTC` through `2023-08-01 23:59:00 UTC` | PROPOSED | This is a date-only selection precedent. It does not establish actual M1 coverage, continuity, complete sessions, or validation capacity. |
| Confirmation | Start: `2023-08-02 00:00:00 UTC`; end: the exact later USD/JPY M1 archive boundary to be observed before export | PROPOSED / PENDING | It is strictly later than evaluation by construction. The exact end timestamp and resulting usable interval must be frozen before export. |

The confirmation interval must never overlap the evaluation interval. It will be
exported into a separate confirmation role directory, checksum-manifested, and
sealed. It must not be opened, previewed, parsed, structurally inspected,
replayed, or used for strategy development unless a later, explicit governance
step authorizes it.

## Native BID/ASK acquisition representation

| Design item | Requirement | Status |
| --- | --- | --- |
| Acquired sides | Acquire one native GMT/UTC M1 **BID** extract and one native GMT/UTC M1 **ASK** extract for each role-selected interval. | PROPOSED |
| Preservation | Preserve each provider-native file unchanged; do not pre-merge, resample, interpolate, or synthesize spread data before freezing. | PROPOSED |
| Pairing key | Future structural validation may pair records only on the exact UTC bar-open timestamp and the same M1 period. | PROPOSED |
| Timestamp alignment | Both extracts must use the identical requested UTC bounds and M1 period. Pair only exact timestamp intersections; no nearest-neighbour or tolerance-based alignment. | PROPOSED |
| Spread derivation | Where exact BID and ASK timestamps exist, the contemporaneous executable spread can be derived from matched BID/ASK values at the relevant price field. The exact formula and field selection remain a future execution-model decision. | PROPOSED |
| Missing side timestamp | Do not impute. Future structural validation must record the affected timestamp as unmatched and exclude it from any future complete-session determination unless a later frozen protocol states another non-discretionary treatment. | PROPOSED |
| Execution-price sufficiency | Matched source-native BID and ASK M1 bars can support a future executable-price model because they preserve both sides rather than infer ASK from an unspecified spread. Sufficiency of the actual files remains unverified until authorized structural validation. | PENDING |

This representation is preferred because Dukascopy documents historical side
selection as BID or ASK. It does not claim that the future files will have
identical timestamps, a particular schema, or any specific completeness level.

## Required manifest facts for each future native file

Each future BID and ASK file requires its own immutable manifest recording:

- candidate ID and role (`evaluation` or `confirmation`);
- provider, instrument, native side, M1 period, and GMT/UTC selection;
- requested UTC start and end timestamps;
- provider-published earliest boundary and observed latest-boundary metadata;
- retrieval timestamp, exact filename, byte size, and SHA-256;
- role-separation and access-control statement.

## Remaining blockers before export authorization

1. **PENDING:** Observe and record the exact current/latest USD/JPY M1 archive
   boundary from Dukascopy metadata without reading rows.
2. **PENDING:** Freeze the confirmation end timestamp from that observed
   boundary, retaining a meaningful later non-overlapping interval.
3. **PENDING:** Create a separate acquisition authorization that pins both
   native sides, the UTC ranges, filenames, output locations, and manifest
   requirements.
4. **PENDING:** After acquisition only, a separately authorized evaluation-only
   structural validation must establish actual schema, BID/ASK timestamp
   matching, precision, missing/duplicate records, continuity, and complete
   session capacity. It must not calculate strategy performance.

## Evidence

- Dukascopy documents USD/JPY BID M1 history from `2003-05-04 21:00 UTC`,
  minute selection, BID/ASK side selection, and GMT/local-time output options:
  [historical-data manual](https://www.dukascopy.com/media/pdf/japan/manual/historical-data.pdf).
- Dukascopy's historical API documents bar retrieval by `Period.ONE_MIN` and
  `OfferSide.BID` / `OfferSide.ASK`:
  [IHistory API](https://www.dukascopy.com/client/javadoc/com/dukascopy/api/IHistory.html).

## Authority boundary

This record grants no authority to download/export data, inspect any row,
create a confirmation file, conduct structural validation, create a strategy,
replay, backtest, optimize, tune, simulate orders, or execute trades.
