# Data Governance

Market data is untrusted until validated. Every dataset requires a source,
license/usage record, acquisition time, coverage, timezone, instrument mapping,
checksum, and immutable version identifier.

Research must use point-in-time data. Corporate actions, symbol changes, missing
bars, duplicate ticks, timezone conversions, and vendor corrections are explicit
transformations with recorded versions. A failed quality check quarantines data;
it cannot silently enter a backtest or live decision path.
