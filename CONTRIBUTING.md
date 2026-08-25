# Contributing

Read the project, architecture, risk, security, and coding-standard documents
before changing code. Propose architectural changes through an ADR.

For strategy work, also read every applicable document in `research/`. Explain
the proposed concept, validation gaps, parameters, and risk assumptions before
writing strategy code. A strategy candidate is never described as production
until it passes the documented promotion gates.

Every change requires focused tests and documentation updates when contracts,
configuration, operations, or behavior change. No secrets, generated market
data, or broker account artifacts may be committed.

Do not add a code path that submits an order without a Risk Engine approval.
