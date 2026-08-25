"""Append-only local journal for the paper-trading workflow."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import UUID

from quantforge.domain.events import DomainEvent


def _json_default(value: object) -> str:
    if isinstance(value, (datetime, Decimal, UUID)):
        return str(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


class SQLiteEventJournal:
    """Durably persist immutable domain events before downstream handling."""

    def __init__(self, path: Path | str) -> None:
        database_path = Path(path)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(database_path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = Lock()
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS event_journal (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    event_type TEXT NOT NULL,
                    schema_version INTEGER NOT NULL,
                    occurred_at_utc TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    causation_id TEXT,
                    payload_json TEXT NOT NULL,
                    checksum TEXT NOT NULL
                )
                """
            )

    def append(self, event: DomainEvent) -> bool:
        """Append once by event ID; return false for an idempotent duplicate."""
        payload = json.dumps(
            dataclasses.asdict(event),
            sort_keys=True,
            separators=(",", ":"),
            default=_json_default,
        )
        checksum = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO event_journal (
                    event_id, event_type, schema_version, occurred_at_utc,
                    correlation_id, causation_id, payload_json, checksum
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event.event_id),
                    type(event).__name__,
                    event.schema_version,
                    event.occurred_at.isoformat(),
                    str(event.correlation_id),
                    str(event.causation_id) if event.causation_id else None,
                    payload,
                    checksum,
                ),
            )
        return cursor.rowcount == 1

    def events(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM event_journal ORDER BY sequence"
            ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        with self._lock:
            self._connection.close()
