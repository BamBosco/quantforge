# QuantForge

QuantForge is a risk-first quantitative trading platform. It is being built
as a modular monolith so research, strategy, risk, execution, and
observability can evolve independently without distributed-systems overhead.

## Safety status

**Research and paper-trading foundation only.** Live trading is disabled by
design. An execution adapter cannot be introduced until the acceptance gates
in [forward-testing policy](docs/FORWARD_TESTING.md) are satisfied and an
operator explicitly authorizes a separate live-release change.

## Architecture at a glance

```text
Market data -> Strategy -> Trade intent -> Risk gate -> Approved order -> Execution
                                  |              |                    |
                                  +--------------+--------------------+
                                             durable audit journal
```

Strategy code never has an execution dependency. The Risk Engine is the only
component permitted to approve a trade intent; execution consumes only
approved orders.

## Repository map

- `src/quantforge/` — production packages, organized by domain boundary.
- `config/` — versioned, non-secret configuration.
- `docs/` — authoritative technical and operational specifications.
- `tests/` — unit, integration, contract, and replay tests.
- `research/` — reproducible experiments; never imported by production code.

Read [Project overview](Project_QuantForge.md), [principles](PRINCIPLES.md),
[architecture](ARCHITECTURE.md), and [risk policy](RISK_ENGINE.md) before
contributing.

## Development status

Version 0.1 establishes the governed foundation. See [the roadmap](docs/ROADMAP.md).

## License

Private project. All rights reserved.
