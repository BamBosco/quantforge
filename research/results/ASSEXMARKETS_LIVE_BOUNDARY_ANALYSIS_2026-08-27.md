# AssexMarkets live boundary analysis

Date: 2026-08-27. This report is generated from the two isolated read-only
receipt databases. A long receipt gap is a **candidate** boundary only; it is
not proof of a broker market closure because a collector, terminal, or network
can also create a gap.

## Current snapshots

| Instrument | Clean accepted receipts | Database total | UTC coverage | Server offset |
| --- | ---: | ---: | --- | --- |
| EURUSD | 52 | 59 | 09:26:05–09:53:28 | 52/52 at UTC+3 |
| XAUUSD | 695 | 695 | 2026-08-26 13:30:08–2026-08-27 09:22:13 | 386/416 exact UTC+3 provenance |

The EURUSD database contains seven preserved pre-attachment XAUUSD receipts;
the analyzer filters them out by `broker_symbol`.

## Boundary detector result

The reproducible command is:

```zsh
.venv/bin/python tools/analyze_assexmarkets_eurusd.py \
  data/assexmarkets_eurusd/mt5_observations.sqlite3 \
  --instrument EURUSD --output research/results/live_boundary_analysis/eurusd.json
```

EURUSD has one 143-second **ordinary collection gap** from
09:26:35Z to 09:28:58Z. It is Thursday, with spreads changing from 15 to
16 points, and is not a daily, rollover, or weekly candidate. The latest
receipt is 09:53:28Z with a 16-point spread.

Applying the same detector to XAUUSD produces long-gap candidates, but the
receipt cadence is too sparse to distinguish an actual metal session break
from collector downtime. No weekly boundary is observed in either stream.
No policy is promoted from these candidates.

The `:8766` and `:8767` receiver processes are running. The MT5 screenshots
show both EA instances attached, but runtime verification shows only EURUSD
posting: EURUSD reached 120 accepted receipts through 10:27:18Z, while XAUUSD
remains at 695 receipts with its last receipt at 09:22:13Z. Attachment is
therefore not sufficient evidence of delivery; the XAUUSD EA's WebRequest
success must be confirmed from a new accepted database receipt. No XAUUSD
boundary conclusion is drawn from the stale stream.

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
- Spread, risk, session, and execution-deviation policies remain in their
  existing provisional states.

## Remaining evidence

Collect continuous receipts through an actual EURUSD daily break, Friday close,
Sunday/Monday reopen, and a DST transition. Obtain broker confirmation of the
`AssexmarketsGlobal-Trade` historical/export timezone and XAUUSD hours,
rollover, holidays, margin, and volume rules.
