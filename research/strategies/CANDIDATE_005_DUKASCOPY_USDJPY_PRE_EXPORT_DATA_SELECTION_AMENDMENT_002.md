# Candidate 005 — Pre-Export Data-Selection Amendment 002

**Candidate ID:** `candidate_005`  
**Status:** **PENDING — aligned selection metadata; no acquisition authorization.**

## Superseding future evaluation selection

For future Candidate 005 acquisition planning, this amendment supersedes only
the previously proposed evaluation end timestamp. The proposed export selection
is now aligned exactly to the Dukascopy MT5 Save As dialog's automatically
provided filename:

`USDJPY_M1_201908010000_202308012300`

| Item | Value | Status |
| --- | --- | --- |
| Instrument | `USDJPY` | VERIFIED |
| Timeframe | `M1` | VERIFIED |
| Proposed evaluation start | `2019-08-01 00:00` | OBSERVED from terminal-provided filename |
| Proposed evaluation end | `2023-08-01 23:00` | OBSERVED from terminal-provided filename |
| Proposed native filename stem | `USDJPY_M1_201908010000_202308012300` | VERIFIED from Save As dialog |
| Export file type offered | CSV/text file | VERIFIED from Save As dialog |

This selection is a source-terminal timestamp selection. It must not be
labelled UTC or New York time until the future acquisition flow visibly records
the terminal/export timestamp basis as GMT/UTC.

## Unchanged controls and blockers

- **PENDING:** explicit GMT/UTC output-basis evidence;
- **PENDING:** native BID/ASK acquisition representation and side selection;
- **PENDING:** latest archive-boundary metadata and later confirmation end;
- **PENDING:** a separate acquisition authorization before an export is
  performed;
- **PENDING:** all post-acquisition structural-quality questions.

No market-data file, including evaluation or confirmation data, is created,
saved, downloaded, opened, parsed, previewed, or analysed by this amendment.
No strategy, replay, optimization, tuning, simulation, or trading activity is
created or authorized.
