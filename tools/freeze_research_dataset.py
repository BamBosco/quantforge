#!/usr/bin/env python3
"""Create a restricted, checksum-recorded manifest without parsing market bars.

This utility deliberately hashes raw bytes only.  It never opens an export as
CSV, derives coverage, or performs a quality assessment; the operator must
record those facts from the export operation and mark quality as unassessed.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("timestamp must include a UTC offset")
    return parsed


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _quoted(value: str) -> str:
    """JSON string syntax is valid TOML basic-string syntax."""
    return json.dumps(value, ensure_ascii=False)


def _viewed_ranges(path: Path, *, venue: str) -> tuple[tuple[datetime, datetime], ...]:
    with path.open("r", encoding="utf-8") as file:
        registry = json.load(file)
    try:
        records = registry["viewed_datasets"]
    except KeyError as error:
        raise ValueError("viewed-data registry has no viewed_datasets records") from error
    ranges: list[tuple[datetime, datetime]] = []
    for record in records:
        if str(record["venue"]) != venue:
            continue
        start = _utc(str(record["start_utc"]))
        end = _utc(str(record["end_utc"]))
        if start >= end:
            raise ValueError("viewed-data registry has an unordered range")
        ranges.append((start, end))
    return tuple(ranges)


def _overlaps(
    start: datetime, end: datetime, ranges: tuple[tuple[datetime, datetime], ...]
) -> bool:
    return any(start < existing_end and existing_start < end for existing_start, existing_end in ranges)


def _frozen_ranges(root: Path) -> tuple[tuple[datetime, datetime], ...]:
    """Read only the declared time section written by this utility's manifests."""
    ranges: list[tuple[datetime, datetime]] = []
    for manifest in root.glob("*/*.manifest.toml"):
        values: dict[str, str] = {}
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if " = " not in line:
                continue
            key, value = line.split(" = ", 1)
            if key in {"start_utc", "end_utc"}:
                values[key] = json.loads(value)
        if set(values) == {"start_utc", "end_utc"}:
            ranges.append((_utc(values["start_utc"]), _utc(values["end_utc"])))
    return tuple(ranges)


def _manifest_value(path: Path, key: str) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key} = "):
            return str(json.loads(line.split(" = ", 1)[1]))
    raise ValueError(f"superseded manifest is missing {key}")


def _validate_supersession(path: Path, raw_file: Path, raw_digest: str) -> None:
    if not path.is_file():
        raise ValueError("superseded manifest does not exist")
    if _manifest_value(path, "raw_filename") != raw_file.name:
        raise ValueError("superseded manifest references another raw export")
    if _manifest_value(path, "sha256") != raw_digest:
        raise ValueError("superseded manifest checksum differs from raw export")


def initialize(root: Path) -> None:
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    for role in ("evaluation", "confirmation"):
        directory = root / role
        directory.mkdir(mode=0o700, exist_ok=True)
        os.chmod(directory, 0o700)


def freeze(args: argparse.Namespace) -> None:
    raw_file = args.raw_file.resolve()
    manifest = args.manifest.resolve()
    root = args.root.resolve()
    role_directory = root / args.role
    if not raw_file.is_file():
        raise ValueError("raw export must be a regular file")
    if raw_file.parent != role_directory.resolve():
        raise ValueError("raw export must be directly inside its restricted role directory")
    if manifest.parent != role_directory.resolve():
        raise ValueError("manifest must be directly inside the same restricted role directory")
    if manifest.exists():
        raise ValueError("refusing to overwrite an existing manifest")
    if args.coverage_start_utc >= args.coverage_end_utc:
        raise ValueError("coverage range must be ordered")
    raw_digest = _sha256(raw_file)
    if _overlaps(
        args.coverage_start_utc,
        args.coverage_end_utc,
        _viewed_ranges(args.viewed_registry.resolve(), venue=args.venue),
    ):
        raise ValueError("declared coverage overlaps previously viewed data")
    if args.supersedes_manifest is not None:
        _validate_supersession(args.supersedes_manifest.resolve(), raw_file, raw_digest)
    elif _overlaps(
        args.coverage_start_utc, args.coverage_end_utc, _frozen_ranges(root)
    ):
        raise ValueError("declared coverage overlaps an already frozen research dataset")

    text = "\n".join(
        (
            "schema_version = \"research_dataset_manifest.v1\"",
            "",
            "[identity]",
            f"dataset_id = {_quoted(args.dataset_id)}",
            f"role = {_quoted(args.role)}",
            f"venue = {_quoted(args.venue)}",
            f"instrument = {_quoted(args.instrument)}",
            f"raw_filename = {_quoted(raw_file.name)}",
            f"sha256 = {_quoted(raw_digest)}",
            "",
            "[provenance]",
            f"source = {_quoted(args.source)}",
            f"acquisition_method = {_quoted(args.acquisition_method)}",
            f"retrieved_at_utc = {_quoted(args.retrieved_at_utc.isoformat())}",
            "",
            "[time]",
            f"source_timezone = {_quoted(args.source_timezone)}",
            f"start_utc = {_quoted(args.coverage_start_utc.isoformat())}",
            f"end_utc = {_quoted(args.coverage_end_utc.isoformat())}",
            "",
            "[quality]",
            "assessment_status = \"unassessed\"",
            "notes = \"Raw export was not parsed before manifest freeze.\"",
            "excluded_session_days = []",
            "",
            "[access_control]",
            "classification = \"unseen_research_data\"",
            "freeze_method = \"owner-read-only raw export and manifest; role directory mode 0700\"",
            *(
                (
                    "",
                    "[supersession]",
                    f"supersedes_manifest = {_quoted(args.supersedes_manifest.name)}",
                    "reason = \"Corrected source timezone provenance without altering raw bytes.\"",
                )
                if args.supersedes_manifest is not None
                else ()
            ),
            "",
        )
    )
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=role_directory, delete=False
    ) as temporary:
        temporary.write(text)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, manifest)
    os.chmod(raw_file, 0o400)
    os.chmod(manifest, 0o400)
    os.chmod(role_directory, 0o700)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create restricted role directories")
    init.add_argument("--root", type=Path, required=True)

    create = commands.add_parser("freeze", help="hash and freeze one raw export")
    create.add_argument("--root", type=Path, required=True)
    create.add_argument("--role", choices=("evaluation", "confirmation"), required=True)
    create.add_argument("--raw-file", type=Path, required=True)
    create.add_argument("--manifest", type=Path, required=True)
    create.add_argument("--viewed-registry", type=Path, required=True)
    create.add_argument("--dataset-id", required=True)
    create.add_argument("--venue", required=True)
    create.add_argument("--instrument", required=True)
    create.add_argument("--source", required=True)
    create.add_argument("--acquisition-method", required=True)
    create.add_argument("--source-timezone", required=True)
    create.add_argument("--retrieved-at-utc", type=_utc, required=True)
    create.add_argument("--coverage-start-utc", type=_utc, required=True)
    create.add_argument("--coverage-end-utc", type=_utc, required=True)
    create.add_argument("--supersedes-manifest", type=Path)
    return result


def main() -> None:
    args = parser().parse_args()
    if args.command == "init":
        initialize(args.root)
    else:
        freeze(args)


if __name__ == "__main__":
    main()
