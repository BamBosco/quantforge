# AssexMarkets live boundary analysis

Date: 2026-08-27. This report is generated from the two isolated read-only
receipt databases. A long receipt gap is a **candidate** boundary only; it is
not proof of a broker market closure because a collector, terminal, or network
can also create a gap.

## Current snapshots

| Instrument | Clean accepted receipts | Database total | UTC coverage | Server offset |
| --- | ---: | ---: | --- | --- |
| EURUSD | 159 | 182 | 09:26:05–10:48:12Z | 159/159 at UTC+3 |
| XAUUSD | 700 | 700 | 2026-08-26 13:30:08–2026-08-27 10:31:39Z | 391/416 exact UTC+3 provenance |

The EURUSD database contains 23 preserved XAUUSD receipts from the
parallel-terminal period; the analyzer filters them out by `broker_symbol`.
The dedicated XAUUSD database remains the source of truth for Candidate 006.
The records span 09:22:53Z–10:41:01Z, use the same account/source identity, and
have no payload-hash overlap with the dedicated XAUUSD database. This pattern
proves that the XAUUSD EA was temporarily configured to post to `:8767`; it is
not a database duplication defect.

## Boundary detector result

The reproducible command is:

```zsh
.venv/bin/python tools/analyze_assexmarkets_eurusd.py \
  data/assexmarkets_eurusd/mt5_observations.sqlite3 \
  --instrument EURUSD --output research/results/live_boundary_analysis/eurusd.json
```

EURUSD has one 143-second **ordinary collection gap** from 09:26:35Z to
09:28:58Z. It is Thursday, with spreads changing from 15 to 16 points, and is
not a daily, rollover, or weekly candidate. The restored XAUUSD stream added
five accepted receipts from 10:29:39Z through 10:31:39Z, with spreads of
24–29 points and exact UTC+3 provenance.

Applying the same detector to XAUUSD produces long-gap candidates, but the
receipt cadence is too sparse to distinguish an actual metal session break
from collector downtime. No weekly boundary is observed in either stream.
No policy is promoted from these candidates.

The `:8766` and `:8767` receiver processes are running with expected-symbol
guards. EURUSD resumed after the guarded restart and reached 159 clean
receipts through 10:48:12Z. XAUUSD remains at 700 through 10:31:39Z, with no
post-restart receipt yet. The EURUSD database also received 23 XAUUSD
receipts during the parallel-terminal period; these remain preserved and
excluded from EURUSD analysis. This confirms delivery recovery, but not
continuous boundary coverage.

The receiver now supports an optional expected-symbol allow-list. It should be
enabled on future dedicated processes (`EURUSD` on `:8767`, `XAUUSD` on
`:8766`) to turn this configuration failure into an explicit HTTP rejection.

## Conclusions

- The shared current AssexMarkets MT5 server clock remains UTC+3.
- EURUSD and XAUUSD have no observed daily break, rollover, Friday close, or
  Sunday/Monday reopen in the available windows.
- EURUSD's published Sunday 21:05–Friday 20:59 GMT+0 schedule and 21:00 GMT+0
  swap statement cannot be reconciled to the observed MT5 clock without broker
  clarification. It is not applied to XAUUSD.
- The live evidence strengthens the current-offset portion of the XAUUSD
  UTC+3 hypothesis, but does not resolve its 2025 historical anomaly or permit
  UTC normalization.
- The five newly restored XAUUSD receipts are ordinary Thursday intraday
  observations; they do not establish a daily break, rollover, weekly close,
  or reopen.
- Spread, risk, session, and execution-deviation policies remain in their
  existing provisional states.

## Remaining evidence

Collect continuous receipts through an actual EURUSD daily break, Friday close,
Sunday/Monday reopen, and a DST transition. Obtain broker confirmation of the
`AssexmarketsGlobal-Trade` historical/export timezone and XAUUSD hours,
rollover, holidays, margin, and volume rules.
