"""Freeze receipt-linked Candidate 006 observations for offline research.

The exporter reads only accepted bridge and Candidate 006 audit records.  It
has no MT5 transport, policy evaluation, or execution dependency.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from quantforge.infrastructure.mt5.observation_contracts import canonical_json
from quantforge.infrastructure.mt5.xauusd_broker_profile_audit import (
    XAUUSDBrokerMetadataObservation,
)


class Candidate006EvidencePackageError(ValueError):
    """Raised when a package cannot prove its bridge-to-audit provenance."""


@dataclass(frozen=True, slots=True)
class Candidate006EvidencePackage:
    records_path: Path
    manifest_path: Path
    records_sha256: str
    record_count: int


def export_candidate_006_evidence_package(
    *,
    observation_database: Path,
    audit_database: Path,
    destination: Path,
) -> Candidate006EvidencePackage:
    """Create immutable JSONL evidence from exact accepted audited receipts."""
    records_path = destination / "candidate_006_xauusd_receipts.jsonl"
    manifest_path = destination / "candidate_006_xauusd_receipts.manifest.json"
    if records_path.exists() or manifest_path.exists():
        raise Candidate006EvidencePackageError("refusing to overwrite evidence package")
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    events = _accepted_events(observation_database)
    audit_payloads = _audit_payloads(audit_database)
    records: list[str] = []
    for event in events:
        source_event_id = event["source_event_id"]
        audit_payload = audit_payloads.get(source_event_id)
        if audit_payload is None:
            continue
        expected = json.loads(
            canonical_json(
                asdict(
                    XAUUSDBrokerMetadataObservation.from_read_only_payload(
                        source_event_id=source_event_id, payload=event["payload"]
                    )
                )
            )
        )
        if audit_payload != expected:
            raise Candidate006EvidencePackageError(
                f"audit payload does not match source receipt {source_event_id}"
            )
        records.append(canonical_json(event))
    if not records:
        raise Candidate006EvidencePackageError(
            "no receipt-linked Candidate 006 observations"
        )
    raw = ("\n".join(records) + "\n").encode()
    digest = sha256(raw).hexdigest()
    manifest = canonical_json(
        {
            "schema_version": "candidate_006_evidence_package.v1",
            "instrument": "XAUUSD",
            "record_count": len(records),
            "records_filename": records_path.name,
            "records_sha256": digest,
            "source_event_ids": [
                json.loads(line)["source_event_id"] for line in records
            ],
            "frozen_at_utc": datetime.now(UTC).isoformat(),
        }
    ).encode() + b"\n"
    _write_once(records_path, raw)
    _write_once(manifest_path, manifest)
    return Candidate006EvidencePackage(
        records_path, manifest_path, digest, len(records)
    )


def verify_candidate_006_evidence_package(destination: Path) -> int:
    """Verify the frozen package checksum and receipt/audit record shape."""
    records_path = destination / "candidate_006_xauusd_receipts.jsonl"
    manifest_path = destination / "candidate_006_xauusd_receipts.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw = records_path.read_bytes()
    if sha256(raw).hexdigest() != manifest.get("records_sha256"):
        raise Candidate006EvidencePackageError("evidence package checksum mismatch")
    records = [json.loads(line) for line in raw.decode().splitlines()]
    if not records or len(records) != manifest.get("record_count"):
        raise Candidate006EvidencePackageError("evidence package record count mismatch")
    if [record["source_event_id"] for record in records] != manifest.get(
        "source_event_ids"
    ):
        raise Candidate006EvidencePackageError("evidence package source IDs mismatch")
    for record in records:
        if (
            record["quality_status"] != "accepted"
            or record["broker_symbol"] != "XAUUSD"
        ):
            raise Candidate006EvidencePackageError(
                "evidence package contains invalid receipt"
            )
        digest = sha256(canonical_json(record["payload"]).encode()).hexdigest()
        if record["payload_sha256"] != digest:
            raise Candidate006EvidencePackageError(
                "source receipt payload checksum mismatch"
            )
    return len(records)


def _accepted_events(database: Path) -> list[dict[str, Any]]:
    connection = sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            """SELECT id, event_time_utc, received_at_utc, payload_json, payload_sha256,
                      quality_status, broker_symbol
               FROM observation_event
               WHERE schema_version = 2 AND source_adapter = 'mt5_read_only_ea'
                 AND broker_profile_id = 'mt5_runtime_observed'
                 AND broker_symbol = 'XAUUSD'
                 AND quality_status = 'accepted' ORDER BY id"""
        ).fetchall()
    finally:
        connection.close()
    return [
        {
            "source_event_id": int(row[0]), "event_time_utc": str(row[1]),
            "received_at_utc": str(row[2]), "payload": json.loads(str(row[3])),
            "payload_sha256": str(row[4]), "quality_status": str(row[5]),
            "broker_symbol": str(row[6]),
        }
        for row in rows
    ]


def _audit_payloads(database: Path) -> dict[int, dict[str, Any]]:
    connection = sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT source_event_id, payload_json "
            "FROM xauusd_broker_metadata_observation"
        ).fetchall()
    finally:
        connection.close()
    return {int(row[0]): json.loads(str(row[1])) for row in rows}


def _write_once(path: Path, data: bytes) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        temporary.write(data)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)
    os.chmod(path, 0o400)
