"""CLI deliberately gated behind a future explicit authorization record."""

from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

from quantforge.backtest.candidate_003 import (
    CANDIDATE_ID,
    CANDIDATE_VERSION,
    EVALUATION_FILENAME,
    EVALUATION_MANIFEST,
    EVALUATION_SHA256,
    PROVENANCE_ADDENDUM,
    load_frozen_evaluation,
    replay_frozen_evaluation,
)
from quantforge.backtest.candidate_003_report import (
    concise_summary,
    write_research_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Authorized Candidate 003 evaluation replay only"
    )
    parser.add_argument("--authorization-record", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument(
        "--results",
        type=Path,
        required=True,
        help="write the deterministic research-only JSON result artifact here",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="perform the already-authorized evaluation replay",
    )
    args = parser.parse_args()
    if not args.authorization_record.is_file():
        raise SystemExit("refusing replay: explicit authorization record is required")
    _verify_authorization(args.authorization_record)
    dataset = load_frozen_evaluation(
        args.evaluation, manifest=args.manifest, provenance=args.provenance
    )
    if not args.execute:
        raise SystemExit("authorization and dataset verified; --execute is required")
    run = replay_frozen_evaluation(
        dataset, quality_exclusions=frozenset(), protocol_path=args.protocol
    )
    report = write_research_report(run, args.results)
    print(concise_summary(report))
    print(f"Research-only result artifact: {args.results}")


def _verify_authorization(path: Path) -> None:
    """Require a minimal, explicit record that binds the sole approved raw file."""
    with path.open("rb") as handle:
        authorization = tomllib.load(handle).get("authorization", {})
    expected = {
        "candidate_id": CANDIDATE_ID,
        "candidate_version": CANDIDATE_VERSION,
        "evaluation_filename": EVALUATION_FILENAME,
        "evaluation_sha256": EVALUATION_SHA256,
        "evaluation_manifest": EVALUATION_MANIFEST,
        "instrument_provenance": PROVENANCE_ADDENDUM,
    }
    if authorization != expected:
        raise SystemExit(
            "refusing replay: authorization record does not exactly bind v0.2"
        )


if __name__ == "__main__":
    main()
