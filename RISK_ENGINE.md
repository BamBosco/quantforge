# Risk Engine Policy

## Authority

The Risk Engine is the non-bypassable pre-trade authority and the only module
allowed to halt trading. No strategy may set its own quantity; it supplies an
entry, stop, target, and rationale through a trade intent.

## Default paper-trading limits

All limits are configuration values, not strategy constants.

| Control | Default | Basis |
|---|---:|---|
| Risk per trade | 1% current equity | Defined, bounded loss |
| Daily drawdown | 3% start-of-day equity | Hard trading halt |
| Total drawdown | 6% peak equity | Hard trading halt |
| Correlated open risk | 3% equity | Prevents hidden concentration |
| Stop loss | required | Every intent must define invalidation |

Position size is calculated from current equity, approved risk fraction,
instrument value per point, and entry-to-stop distance. The engine rejects
missing, stale, malformed, or non-positive inputs.

The current offline implementation applies these limits before any order can
exist: protective-stop shape, daily drawdown, total drawdown, correlated open
risk, broker volume bounds, and step-aligned risk sizing. It produces a
non-executable risk decision; execution integration remains unavailable.

## Kill switch

On a daily or total drawdown breach, the system records the breach, prevents
new approvals, disables strategies, requests controlled flattening, and
requires an explicit manual review before any resumption. It never resumes
automatically.

## Scheduled news and event risk

Scheduled high-impact events require an independent, Risk-Engine-owned
blackout and flattening policy. The proposed initial policy closes affected
open positions and cancels entries three hours before a covered event; it never
waits for a loss to recover. See the detailed
[scheduled news and event risk policy](docs/NEWS_EVENT_RISK_POLICY.md).

## Open policy decisions

Risk-of-ruin gate, consecutive-loss breaker, and correlation methodology must
be empirically specified before they can become enforceable controls.
