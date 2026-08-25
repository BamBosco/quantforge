#!/usr/bin/env python3
"""Export and verify immutable receipt-linked Candidate 006 evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from quantforge.infrastructure.mt5.xauusd_evidence_package import (
    export_candidate_006_evidence_package,
    verify_candidate_006_evidence_package,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    arguments = parser.parse_args()
    package = export_candidate_006_evidence_package(
        observation_database=arguments.observations,
        audit_database=arguments.audit,
        destination=arguments.destination,
    )
    count = verify_candidate_006_evidence_package(arguments.destination)
    print(f"frozen {count} receipts")
    print(package.manifest_path)


if __name__ == "__main__":
    main()
