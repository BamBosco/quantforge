# Coding Standards

Python code uses type hints, small focused modules, immutable value objects for
domain messages, UTC-aware timestamps, `Decimal` where monetary precision
matters, and explicit error handling. Public APIs require docstrings.

Tests are behavioral and deterministic. Code must not hardcode configuration,
depend on vendor types outside infrastructure, perform I/O in domain logic, or
duplicate risk calculations. Pull requests include tests, relevant documentation,
and an ADR for architecture changes.
