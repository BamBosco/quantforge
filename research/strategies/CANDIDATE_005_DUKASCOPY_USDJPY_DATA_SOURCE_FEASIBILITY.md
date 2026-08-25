# Candidate 005 — Dukascopy USD/JPY Data-Source Feasibility Intake

**Candidate ID:** `candidate_005`  
**Scope:** data-source feasibility / intake only  
**Instrument:** `USD/JPY` / `USDJPY`  
**Provider:** Dukascopy Bank SA historical-data service  
**Assessment status:** **PASS — preliminary source capability only.**

This is not a trading strategy, data-selection authorization, export
authorization, structural-quality assessment, replay, backtest, optimization,
or execution authority. No Candidate 005 market-data file was downloaded,
opened, parsed, previewed, or analysed for this record. No confirmation dataset
exists or was accessed.

## Proposed evaluation precedent (not authorization)

`2019-08-01 00:00:00 UTC` through `2023-08-01 23:59:00 UTC` is used only as a
proposed chronological evaluation precedent. It is not a frozen range, it
creates no dataset, and it does not choose any strategy rule or parameter.

## Evidence and feasibility classification

| Question | Finding | Status | Evidence / limitation |
| --- | --- | --- | --- |
| USD/JPY availability | `USD/JPY` is a listed Dukascopy instrument. | VERIFIED | Dukascopy's Instrument API lists `USDJPY`; its historical-data manual specifically identifies USD/JPY. |
| Genuine M1 availability | Dukascopy states that USD/JPY BID one-minute history is available from `2003-05-04 21:00 UTC`. | VERIFIED | The entire proposed 2019-08-01 to 2023-08-01 interval falls after that published boundary. |
| Historical boundaries | Published earliest USD/JPY BID M1 boundary: `2003-05-04 21:00 UTC`. Latest boundary is not fixed in this record. | VERIFIED / PENDING | Earliest is provider-published; current latest availability must be observed as metadata immediately before later range selection. |
| M1 period support | JForex exposes `Period.ONE_MIN`. | VERIFIED | Provider API documentation. |
| Timestamp basis | Dukascopy's historical-data facility permits `GMT` output (and separately a local-time option). | VERIFIED | Future acquisition must explicitly select GMT/UTC; a local-time export is not permitted for Candidate 005. |
| DST and New York conversion | With a GMT/UTC export, source timestamps have no source-DST ambiguity; convert each instant using the IANA `America/New_York` timezone database. | VERIFIED, conditional on GMT selection | This is a deterministic UTC-to-New-York conversion, including DST transitions. |
| OHLC precision / increment | Dukascopy states JPY pairs quote to the third decimal place, equivalent to a `0.001` minimum quoted increment (0.1 pip). | VERIFIED for quoted increment | Actual CSV decimal representation and the exact OHLC column labels remain unverified until later structural validation. |
| Bid / ask availability | Historical download settings support independently selecting BID or ASK. JForex historical-bar API also accepts an offer side. | VERIFIED | Future intake must preserve an explicitly documented side choice; a single BID-only file does not itself establish executable ASK prices. |
| Defensible execution-price model | A model is potentially supportable by matched UTC BID and ASK historical extracts, or by a source-native per-bar spread field if the actual export supplies one. | PENDING | Exact export schema, timestamp alignment, and spread/ask sufficiency must be verified after a role-specific evaluation dataset is frozen and separately authorized for structural inspection. |
| Missing / duplicate / continuity facts | Not established. | PENDING | These are row-level properties and are intentionally out of scope for this intake. |
| Capacity for existing validation protocol | Four calendar years of weekday dates provide substantial potential capacity above the existing `>=709` valid-session gate. | VERIFIED as calendar potential only | Complete sessions, exclusions, and strategy-specific eligibility cannot be established before strategy definition and authorized structural validation. |
| Later non-overlapping confirmation | Potentially maintainable, because the source has published USD/JPY M1 history beginning in 2003 and current historical access. | PENDING | Freeze a later interval only after the then-current latest archive boundary is observed as source metadata. It must be strictly later than the final evaluation boundary. |

## Source facts and interpretation controls

1. The provider documents USD/JPY historical data in UTC/GMT terms. Candidate
   005 must use the GMT option, record that choice in its future manifest, and
   treat timestamps as UTC instants. No broker-server local-time assumption is
   allowed.
2. BID and ASK are selectable sides rather than evidence that an unspecified
   CSV already contains both sides. The later data-selection record must state
   whether it acquires matched native BID and ASK extracts or another
   source-native representation that demonstrably supports executable prices.
3. The `0.001` quote increment is source instrument information, not a finding
   about any uninspected CSV's formatting or continuity.
4. This PASS does not validate rows, field values, timestamps, spreads,
   calendar completeness, strategy capacity, or performance.

## Evidence sources

- Dukascopy historical-data manual: USD/JPY BID M1 history available from
  `2003-05-04 21:00 UTC`; historical selection supports minute granularity,
  BID/ASK side, and GMT or local-time output.
  [Dukascopy historical-data manual](https://www.dukascopy.com/media/pdf/japan/manual/historical-data.pdf)
- Dukascopy JForex API: historical bars can be requested by instrument,
  `Period.ONE_MIN`, and `OfferSide.BID` or `OfferSide.ASK`.
  [IHistory API](https://www.dukascopy.com/client/javadoc/com/dukascopy/api/IHistory.html)
- Dukascopy API: `USDJPY` is a defined instrument and exposes pip/tick-scale
  metadata.
  [Instrument API](https://www.dukascopy.com/client/javadoc3/com/dukascopy/api/Instrument.html)
- Dukascopy Japan instrument information: JPY pairs use third-decimal quote
  precision / 0.1-pip increments.
  [Dukascopy JPY quoting information](https://www.dukascopy.com/media-storage/1582429748/i/)

## Decision and smallest next step

**Decision: PASS — Dukascopy is a feasible prospective Candidate 005 USD/JPY
M1 source, conditional on UTC/GMT acquisition and later structural validation.**

The smallest next step is to create a Candidate 005 **pre-export data-selection
record**. It must predeclare the UTC evaluation range, observe the current
latest archive boundary as non-row metadata, select a strictly later
non-overlapping confirmation range, and specify the native BID/ASK acquisition
representation. It must not export or inspect any data.
