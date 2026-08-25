# Crabel ORB Review

## Scope and source

This note reviews the opening-range material in Section I of Toby Crabel's
*Day Trading with Short Term Price Patterns and Opening Range Breakout*.
The source is a scanned historical futures-trading text. Its examples and
statistics must not be assumed to transfer to modern FX, CFD, equity, or
crypto markets.

## What the source describes

Crabel's basic ORB places buy and sell stop entries outside an opening range,
offset by a volatility-derived quantity called `Stretch`. The first side reached
opens the position; the opposite side is used as protection. A directional
variant (ORBP) places only the order aligned with a pre-existing market bias.

`Stretch` is described as a rolling ten-day average of the distance from each
daily open to that day's nearer extreme. This is a source-derived definition,
not a validated QuantForge parameter.

The text also treats the first 5-10 minutes as potentially informative. It
describes early directional movement, narrow-range/inside-day conditions,
gaps, prior-day structure, and volume as possible contextual inputs. These are
separate hypotheses, not a single proven filter set.

## Source-derived implementation implications

- The underlying entry is a breakout stop order, not a signal at bar close.
- An unambiguous session calendar and opening timestamp are required.
- The breakout buffer requires point-in-time daily-open and daily-extreme data.
- Two-sided entry requires OCO behavior: when one side fills, the other must be
  cancelled immediately and idempotently.
- Intraday data of at least 1-minute resolution is required; 5-minute bars are
  necessary for examining the early-entry hypothesis.

## QuantForge safety changes

The source's protective-order timing cannot override QuantForge policy. A
QuantForge trade intent must include a defined stop before Risk Engine approval.
We will not wait until after entry to establish the maximum permitted loss.

The source discusses scaling, break-even moves, trailing stops, and discretionary
context. These are not included in the initial candidate because they introduce
too many degrees of freedom. They may be independently tested later.

## Validation risks

- Historical examples are not a reproducible modern performance study.
- The source uses legacy futures contracts, session conventions, tick sizes, and
  market microstructure different from a future MT5 venue.
- The opening session, range duration, order-fill model, and stop logic are not
  a complete machine-readable strategy specification in the source.
- Combining early entry, gaps, inside days, range conditions, and volume filters
  without a predeclared plan would create high data-mining risk.

## QuantForge conclusion

The book provides a useful ORB hypothesis and several testable feature ideas.
It does not prove a portable trading edge and does not choose QuantForge's
market, session, risk limits, or exit logic. The decisions required before
backtest implementation are in [the ORB decision sheet](../strategies/ORB_DECISION_SHEET.md).
