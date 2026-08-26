"""Durable, append-only storage for read-only MT5 observations.

The log records every receipt, including duplicate or degraded observations. It
does not issue instructions to MT5 and contains no execution capability.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from quantforge.infrastructure.mt5.observation_contracts import (
    ObservationEnvelope,
    canonical_json,
    payload_sha256,
)
from quantforge.infrastructure.mt5.observation_quality import (
    ObservationQualityPolicy,
    assess_observation,
)


class ObservationLogError(RuntimeError):
    """Raised when the append-only observation log cannot persist a record."""


@dataclass(frozen=True, slots=True)
class StoredObservation:
    """Immutable receipt metadata for one persisted observation."""

    id: int
    observation_id: str
    schema_version: int
    received_at_utc: datetime
    quality_status: str
    quality_issues: tuple[str, ...]


class SQLiteMarketObservationLog:
    """Local SQLite audit log for market and account observations only."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        quality_policy: ObservationQualityPolicy | None = None,
    ) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = Lock()
        self._quality_policy = quality_policy or ObservationQualityPolicy()
        self._bootstrap()

    def _bootstrap(self) -> None:
        with self._connection:
            # Retained for compatibility with the original v1 bridge log.
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_observation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observed_at_utc TEXT NOT NULL,
                    account_login INTEGER NOT NULL,
                    broker_server TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    bid REAL NOT NULL,
                    ask REAL NOT NULL,
                    spread_points INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_fingerprint TEXT NOT NULL UNIQUE
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS observation_event (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observation_id TEXT NOT NULL,
                    schema_version INTEGER NOT NULL,
                    source_adapter TEXT NOT NULL,
                    broker_profile_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    broker_symbol TEXT NOT NULL,
                    event_time_utc TEXT NOT NULL,
                    received_at_utc TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    quality_status TEXT NOT NULL,
                    quality_issues_json TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_observation_event_scope
                ON observation_event (source_adapter, broker_profile_id, account_id,
                                      broker_symbol, id)
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS research_market_snapshot (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observation_id TEXT NOT NULL UNIQUE,
                    candle_open_time_utc TEXT,
                    validation_status TEXT NOT NULL,
                    validation_issues_json TEXT NOT NULL,
                    snapshot_json TEXT,
                    created_at_utc TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_decision (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observation_id TEXT NOT NULL UNIQUE,
                    decision_status TEXT NOT NULL,
                    rejection_reasons_json TEXT NOT NULL,
                    agent_decision_json TEXT NOT NULL,
                    trade_intent_json TEXT,
                    created_at_utc TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS decision_quality_evaluation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    decision_observation_id TEXT NOT NULL UNIQUE,
                    evaluation_status TEXT NOT NULL,
                    evaluation_json TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS risk_decision (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observation_id TEXT NOT NULL UNIQUE,
                    risk_status TEXT NOT NULL,
                    risk_decision_json TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_request (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observation_id TEXT NOT NULL UNIQUE,
                    request_status TEXT NOT NULL,
                    validation_issues_json TEXT NOT NULL,
                    request_json TEXT,
                    created_at_utc TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS one_time_demo_readiness (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    authorization_scope TEXT NOT NULL UNIQUE,
                    observation_id TEXT NOT NULL UNIQUE,
                    nonce TEXT NOT NULL UNIQUE,
                    readiness_status TEXT NOT NULL,
                    checks_json TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    account_state_json TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS demo_position_state_observation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observation_id TEXT NOT NULL UNIQUE,
                    observation_timestamp_utc TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    broker_symbol TEXT NOT NULL,
                    validation_status TEXT NOT NULL,
                    validation_issues_json TEXT NOT NULL,
                    state_json TEXT,
                    created_at_utc TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS demo_execution_receipt_reconciliation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    readiness_observation_id TEXT NOT NULL UNIQUE,
                    position_state_observation_id TEXT NOT NULL,
                    reconciliation_status TEXT NOT NULL,
                    broker_response_json TEXT NOT NULL,
                    reconciliation_json TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_account_equity_baseline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    account_server TEXT NOT NULL,
                    broker_symbol TEXT NOT NULL,
                    baseline_date_utc TEXT NOT NULL,
                    source_observation_id TEXT NOT NULL,
                    source_observation_timestamp_utc TEXT NOT NULL,
                    equity TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    UNIQUE (
                        account_id, account_server, broker_symbol, baseline_date_utc
                    )
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS candidate_006_non_live_readiness (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observation_id TEXT NOT NULL UNIQUE,
                    readiness_status TEXT NOT NULL,
                    checks_json TEXT NOT NULL,
                    artifact_json TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                )
                """
            )

    def append(self, snapshot: Any) -> str:
        """Persist a bridge v1 snapshot as one normalized v2 audit event."""
        public_payload = (
            snapshot.to_public_payload()
            if hasattr(snapshot, "to_public_payload")
            else snapshot.public_payload()
        )
        stored = self.append_observation(
            ObservationEnvelope.from_payload(public_payload)
        )
        return stored.observation_id

    def append_observation(self, observation: ObservationEnvelope) -> StoredObservation:
        """Append one observation receipt, even if it is duplicate or degraded."""

        received_at_utc = datetime.now(UTC)
        payload_json = canonical_json(observation.payload)
        payload_digest = payload_sha256(observation.payload)
        with self._lock, self._connection:
            rows = self._connection.execute(
                """
                SELECT payload_sha256, event_time_utc
                FROM observation_event
                WHERE source_adapter = ? AND broker_profile_id = ?
                  AND account_id = ? AND broker_symbol = ?
                ORDER BY id DESC
                LIMIT 128
                """,
                (
                    observation.source_adapter,
                    observation.broker_profile_id,
                    observation.account_id,
                    observation.broker_symbol,
                ),
            ).fetchall()
            previous_observed_at_utc = (
                datetime.fromisoformat(str(rows[0]["event_time_utc"])) if rows else None
            )
            assessment = assess_observation(
                observation,
                received_at_utc=received_at_utc,
                previous_payload_sha256=(
                    str(rows[0]["payload_sha256"]) if rows else None
                ),
                previous_event_time_utc=previous_observed_at_utc,
                policy=self._quality_policy,
            )
            cursor = self._connection.execute(
                """
                INSERT INTO observation_event (
                    observation_id, schema_version, source_adapter, broker_profile_id,
                    account_id, broker_symbol, event_time_utc, received_at_utc,
                    payload_json, payload_sha256, quality_status, quality_issues_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    observation.observation_id,
                    observation.schema_version,
                    observation.source_adapter,
                    observation.broker_profile_id,
                    observation.account_id,
                    observation.broker_symbol,
                    observation.observed_at_utc.isoformat(),
                    received_at_utc.isoformat(),
                    payload_json,
                    payload_digest,
                    assessment.quality_status,
                    json.dumps(list(assessment.issues), separators=(",", ":")),
                ),
            )
        return StoredObservation(
            id=int(cursor.lastrowid or 0),
            observation_id=observation.observation_id,
            schema_version=observation.schema_version,
            received_at_utc=received_at_utc,
            quality_status=assessment.quality_status,
            quality_issues=assessment.issues,
        )

    def recent_observations(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """Return audit metadata and payloads for local forensic inspection."""

        if limit < 1:
            raise ValueError("limit must be positive")
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM observation_event ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "observation_id": str(row["observation_id"]),
                "schema_version": int(row["schema_version"]),
                "source_adapter": str(row["source_adapter"]),
                "broker_profile_id": str(row["broker_profile_id"]),
                "account_id": str(row["account_id"]),
                "broker_symbol": str(row["broker_symbol"]),
                "event_time_utc": str(row["event_time_utc"]),
                "received_at_utc": str(row["received_at_utc"]),
                "quality_status": str(row["quality_status"]),
                "quality_issues": json.loads(str(row["quality_issues_json"])),
                "payload": json.loads(str(row["payload_json"])),
            }
            for row in rows
        ]

    def observations_for_account_day(
        self,
        *,
        account_id: str,
        broker_symbol: str,
        day_start_utc: datetime,
        day_end_utc: datetime,
    ) -> list[dict[str, Any]]:
        """Return accepted raw observations for one account/symbol UTC day."""
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT observation_id, event_time_utc, payload_json
                FROM observation_event
                WHERE account_id = ? AND broker_symbol = ?
                  AND quality_status = 'accepted'
                  AND event_time_utc >= ? AND event_time_utc < ?
                ORDER BY event_time_utc ASC, id ASC
                """,
                (
                    account_id,
                    broker_symbol,
                    day_start_utc.isoformat(),
                    day_end_utc.isoformat(),
                ),
            ).fetchall()
        return [
            {
                "observation_id": str(row["observation_id"]),
                "event_time_utc": str(row["event_time_utc"]),
                "payload": json.loads(str(row["payload_json"])),
            }
            for row in rows
        ]

    def append_daily_account_equity_baseline(
        self,
        *,
        account_id: str,
        account_server: str,
        broker_symbol: str,
        baseline_date_utc: str,
        source_observation_id: str,
        source_observation_timestamp_utc: str,
        equity: str,
    ) -> bool:
        """Append one immutable earliest-observation equity baseline per UTC day."""
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO daily_account_equity_baseline (
                    account_id, account_server, broker_symbol, baseline_date_utc,
                    source_observation_id, source_observation_timestamp_utc, equity,
                    created_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account_id,
                    account_server,
                    broker_symbol,
                    baseline_date_utc,
                    source_observation_id,
                    source_observation_timestamp_utc,
                    equity,
                    datetime.now(UTC).isoformat(),
                ),
            )
        return cursor.rowcount == 1

    def daily_account_equity_baseline(
        self,
        *,
        account_id: str,
        account_server: str,
        broker_symbol: str,
        baseline_date_utc: str,
    ) -> dict[str, Any] | None:
        """Return one immutable daily account-equity baseline."""
        with self._lock:
            row = self._connection.execute(
                """
                SELECT * FROM daily_account_equity_baseline
                WHERE account_id = ? AND account_server = ? AND broker_symbol = ?
                  AND baseline_date_utc = ?
                """,
                (account_id, account_server, broker_symbol, baseline_date_utc),
            ).fetchone()
        if row is None:
            return None
        return {
            "account_id": str(row["account_id"]),
            "account_server": str(row["account_server"]),
            "broker_symbol": str(row["broker_symbol"]),
            "baseline_date_utc": str(row["baseline_date_utc"]),
            "source_observation_id": str(row["source_observation_id"]),
            "source_observation_timestamp_utc": str(
                row["source_observation_timestamp_utc"]
            ),
            "equity": str(row["equity"]),
            "created_at_utc": str(row["created_at_utc"]),
        }

    def append_research_snapshot(
        self,
        *,
        observation_id: str,
        candle_open_time_utc: datetime | None,
        validation_status: str,
        validation_issues: tuple[str, ...],
        snapshot: dict[str, Any] | None,
    ) -> bool:
        """Persist one non-executable research snapshot or its rejection reason.

        The unique observation identifier makes consumption idempotent. The
        database records rejected observations too, so an absent market snapshot
        cannot hide a stale or malformed input from later audit.
        """
        if validation_status not in {"accepted", "rejected"}:
            raise ValueError("validation_status must be accepted or rejected")
        snapshot_json = canonical_json(snapshot) if snapshot is not None else None
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO research_market_snapshot (
                    observation_id, candle_open_time_utc, validation_status,
                    validation_issues_json, snapshot_json, created_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    observation_id,
                    candle_open_time_utc.isoformat()
                    if candle_open_time_utc is not None
                    else None,
                    validation_status,
                    json.dumps(list(validation_issues), separators=(",", ":")),
                    snapshot_json,
                    datetime.now(UTC).isoformat(),
                ),
            )
        return cursor.rowcount == 1

    def research_snapshots(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """Return persisted research-layer inputs and validation outcomes."""
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM research_market_snapshot ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "observation_id": str(row["observation_id"]),
                "candle_open_time_utc": row["candle_open_time_utc"],
                "validation_status": str(row["validation_status"]),
                "validation_issues": json.loads(str(row["validation_issues_json"])),
                "created_at_utc": str(row["created_at_utc"]),
                "snapshot": json.loads(str(row["snapshot_json"]))
                if row["snapshot_json"] is not None
                else None,
            }
            for row in rows
        ]

    def latest_accepted_research_snapshot(self) -> dict[str, Any] | None:
        """Return only a snapshot that passed deterministic market validation."""
        with self._lock:
            row = self._connection.execute(
                """
                SELECT * FROM research_market_snapshot
                WHERE validation_status = 'accepted'
                ORDER BY id DESC LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        snapshot = json.loads(str(row["snapshot_json"]))
        assert isinstance(snapshot, dict)
        return {
            "observation_id": str(row["observation_id"]),
            "snapshot": snapshot,
            "created_at_utc": str(row["created_at_utc"]),
        }

    def research_snapshot_for_observation(
        self, observation_id: str
    ) -> dict[str, Any] | None:
        """Return one normalized snapshot and validation result by observation ID."""
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM research_market_snapshot WHERE observation_id = ?",
                (observation_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "observation_id": str(row["observation_id"]),
            "validation_status": str(row["validation_status"]),
            "validation_issues": json.loads(str(row["validation_issues_json"])),
            "snapshot": json.loads(str(row["snapshot_json"]))
            if row["snapshot_json"] is not None
            else None,
            "created_at_utc": str(row["created_at_utc"]),
        }

    def append_agent_decision(
        self,
        *,
        observation_id: str,
        status: str,
        reasons: tuple[str, ...],
        agent_decision: dict[str, Any],
        trade_intent: dict[str, Any] | None,
    ) -> bool:
        """Persist a non-executable agent result exactly once per observation."""
        if status not in {"accepted", "rejected"}:
            raise ValueError("status must be accepted or rejected")
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO agent_decision (
                    observation_id, decision_status, rejection_reasons_json,
                    agent_decision_json, trade_intent_json, created_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    observation_id,
                    status,
                    json.dumps(list(reasons)),
                    canonical_json(agent_decision),
                    canonical_json(trade_intent) if trade_intent is not None else None,
                    datetime.now(UTC).isoformat(),
                ),
            )
        return cursor.rowcount == 1

    def agent_decision_for_observation(
        self, observation_id: str
    ) -> dict[str, Any] | None:
        """Return the one audited research decision for an observation, if any."""
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM agent_decision WHERE observation_id = ?",
                (observation_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "observation_id": str(row["observation_id"]),
            "status": str(row["decision_status"]),
            "reasons": json.loads(str(row["rejection_reasons_json"])),
            "agent_decision": json.loads(str(row["agent_decision_json"])),
            "trade_intent": json.loads(str(row["trade_intent_json"]))
            if row["trade_intent_json"] is not None
            else None,
            "created_at_utc": str(row["created_at_utc"]),
        }

    def agent_decisions(self, *, limit: int = 100) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM agent_decision ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {
                "observation_id": str(row["observation_id"]),
                "status": str(row["decision_status"]),
                "reasons": json.loads(str(row["rejection_reasons_json"])),
                "agent_decision": json.loads(str(row["agent_decision_json"])),
                "trade_intent": json.loads(str(row["trade_intent_json"]))
                if row["trade_intent_json"] is not None
                else None,
                "created_at_utc": str(row["created_at_utc"]),
            }
            for row in rows
        ]

    def append_decision_quality_evaluation(
        self,
        *,
        decision_observation_id: str,
        evaluation_status: str,
        evaluation: dict[str, Any],
    ) -> bool:
        """Persist one idempotent, non-executable level-observation evaluation."""
        if evaluation_status not in {"evaluated", "skipped"}:
            raise ValueError("evaluation_status must be evaluated or skipped")
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO decision_quality_evaluation (
                    decision_observation_id, evaluation_status, evaluation_json,
                    created_at_utc
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    decision_observation_id,
                    evaluation_status,
                    canonical_json(evaluation),
                    datetime.now(UTC).isoformat(),
                ),
            )
        return cursor.rowcount == 1

    def decision_quality_evaluations(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """Return durable research-only decision-quality observations."""
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM decision_quality_evaluation
                ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "decision_observation_id": str(row["decision_observation_id"]),
                "status": str(row["evaluation_status"]),
                "evaluation": json.loads(str(row["evaluation_json"])),
                "created_at_utc": str(row["created_at_utc"]),
            }
            for row in rows
        ]

    def append_risk_decision(
        self, *, observation_id: str, risk_status: str, risk_decision: dict[str, Any]
    ) -> bool:
        """Persist a non-executable deterministic risk outcome exactly once."""
        if risk_status not in {"approved", "rejected", "not_applicable"}:
            raise ValueError("invalid risk status")
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO risk_decision (
                    observation_id, risk_status, risk_decision_json, created_at_utc
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    observation_id,
                    risk_status,
                    canonical_json(risk_decision),
                    datetime.now(UTC).isoformat(),
                ),
            )
        return cursor.rowcount == 1

    def risk_decisions(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """Return deterministic, non-executable risk-gate results."""
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM risk_decision ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {
                "observation_id": str(row["observation_id"]),
                "status": str(row["risk_status"]),
                "risk_decision": json.loads(str(row["risk_decision_json"])),
                "created_at_utc": str(row["created_at_utc"]),
            }
            for row in rows
        ]

    def risk_decision_for_observation(
        self, observation_id: str
    ) -> dict[str, Any] | None:
        """Return the one deterministic risk result for an observation, if present."""
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM risk_decision WHERE observation_id = ?",
                (observation_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "observation_id": str(row["observation_id"]),
            "status": str(row["risk_status"]),
            "risk_decision": json.loads(str(row["risk_decision_json"])),
            "created_at_utc": str(row["created_at_utc"]),
        }

    def append_execution_request(
        self,
        *,
        observation_id: str,
        request_status: str,
        validation_issues: tuple[str, ...],
        request: dict[str, Any] | None,
    ) -> bool:
        """Persist an unsendable Stage-A request exactly once for audit review."""
        if request_status not in {"constructed", "rejected"}:
            raise ValueError("invalid execution request status")
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO execution_request (
                    observation_id, request_status, validation_issues_json,
                    request_json, created_at_utc
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    observation_id,
                    request_status,
                    json.dumps(list(validation_issues), separators=(",", ":")),
                    canonical_json(request) if request is not None else None,
                    datetime.now(UTC).isoformat(),
                ),
            )
        return cursor.rowcount == 1

    def execution_requests(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """Return Stage-A constructed/rejected requests; none can be submitted."""
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM execution_request ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {
                "observation_id": str(row["observation_id"]),
                "status": str(row["request_status"]),
                "validation_issues": json.loads(str(row["validation_issues_json"])),
                "request": json.loads(str(row["request_json"]))
                if row["request_json"] is not None
                else None,
                "created_at_utc": str(row["created_at_utc"]),
            }
            for row in rows
        ]

    def append_one_time_demo_readiness(
        self,
        *,
        authorization_scope: str,
        observation_id: str,
        nonce: str,
        checks: tuple[str, ...],
        request: dict[str, Any],
        account_state: dict[str, Any],
    ) -> bool:
        """Record one non-executable, unclaimed demo-order readiness token.

        This is deliberately not a submission queue.  The only status written
        by this repository phase is ``ready_unclaimed``; a separate, reviewed
        broker transport would need to consume a token explicitly.
        """
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO one_time_demo_readiness (
                    authorization_scope, observation_id, nonce, readiness_status,
                    checks_json, request_json, account_state_json, created_at_utc
                ) VALUES (?, ?, ?, 'ready_unclaimed', ?, ?, ?, ?)
                """,
                (
                    authorization_scope,
                    observation_id,
                    nonce,
                    json.dumps(list(checks), separators=(",", ":")),
                    canonical_json(request),
                    canonical_json(account_state),
                    datetime.now(UTC).isoformat(),
                ),
            )
        return cursor.rowcount == 1

    def append_candidate_006_non_live_readiness(
        self,
        *,
        observation_id: str,
        readiness_status: str,
        checks: tuple[str, ...],
        artifact: dict[str, Any],
    ) -> bool:
        """Persist Candidate 006 readiness for paper/simulation only.

        This is deliberately separate from the legacy one-time USDJPY demo
        readiness record: it records no authorization token and cannot be
        consumed by a broker transport.
        """
        if readiness_status not in {"ready_non_live", "not_ready"}:
            raise ValueError("invalid Candidate 006 non-live readiness status")
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO candidate_006_non_live_readiness (
                    observation_id, readiness_status, checks_json, artifact_json,
                    created_at_utc
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    observation_id,
                    readiness_status,
                    json.dumps(list(checks), separators=(",", ":")),
                    canonical_json(artifact),
                    datetime.now(UTC).isoformat(),
                ),
            )
        return cursor.rowcount == 1

    def candidate_006_non_live_readiness(
        self, observation_id: str
    ) -> dict[str, Any] | None:
        """Return the immutable Candidate 006 paper/simulation readiness artifact."""
        with self._lock:
            row = self._connection.execute(
                """
                SELECT * FROM candidate_006_non_live_readiness
                WHERE observation_id = ?
                """,
                (observation_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "observation_id": str(row["observation_id"]),
            "status": str(row["readiness_status"]),
            "checks": json.loads(str(row["checks_json"])),
            "artifact": json.loads(str(row["artifact_json"])),
            "created_at_utc": str(row["created_at_utc"]),
        }

    def append_demo_position_state_observation(
        self,
        *,
        observation_id: str,
        observation_timestamp_utc: str,
        account_id: str,
        broker_symbol: str,
        validation_status: str,
        validation_issues: tuple[str, ...],
        state: dict[str, Any] | None,
    ) -> bool:
        """Persist one read-only USDJPY demo position-state observation."""
        if validation_status not in {"accepted", "rejected"}:
            raise ValueError("invalid position-state validation status")
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO demo_position_state_observation (
                    observation_id, observation_timestamp_utc, account_id,
                    broker_symbol, validation_status, validation_issues_json,
                    state_json, created_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    observation_id,
                    observation_timestamp_utc,
                    account_id,
                    broker_symbol,
                    validation_status,
                    json.dumps(list(validation_issues), separators=(",", ":")),
                    canonical_json(state) if state is not None else None,
                    datetime.now(UTC).isoformat(),
                ),
            )
        return cursor.rowcount == 1

    def demo_position_state_observations(
        self, *, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Return persisted read-only USDJPY demo position-state observations."""
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM demo_position_state_observation
                ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "observation_id": str(row["observation_id"]),
                "observation_timestamp_utc": str(row["observation_timestamp_utc"]),
                "account_id": str(row["account_id"]),
                "broker_symbol": str(row["broker_symbol"]),
                "validation_status": str(row["validation_status"]),
                "validation_issues": json.loads(str(row["validation_issues_json"])),
                "state": json.loads(str(row["state_json"]))
                if row["state_json"] is not None
                else None,
                "created_at_utc": str(row["created_at_utc"]),
            }
            for row in rows
        ]

    def demo_position_state_observation_for_observation(
        self, observation_id: str
    ) -> dict[str, Any] | None:
        """Return one persisted read-only position-state observation by ID."""
        with self._lock:
            row = self._connection.execute(
                """
                SELECT * FROM demo_position_state_observation
                WHERE observation_id = ?
                """,
                (observation_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "observation_id": str(row["observation_id"]),
            "observation_timestamp_utc": str(row["observation_timestamp_utc"]),
            "account_id": str(row["account_id"]),
            "broker_symbol": str(row["broker_symbol"]),
            "validation_status": str(row["validation_status"]),
            "validation_issues": json.loads(str(row["validation_issues_json"])),
            "state": json.loads(str(row["state_json"]))
            if row["state_json"] is not None
            else None,
            "created_at_utc": str(row["created_at_utc"]),
        }

    def append_demo_execution_receipt_reconciliation(
        self,
        *,
        readiness_observation_id: str,
        position_state_observation_id: str,
        reconciliation_status: str,
        broker_response: dict[str, Any],
        reconciliation: dict[str, Any],
    ) -> bool:
        """Append one immutable manual-demo broker receipt reconciliation."""
        if reconciliation_status not in {
            "confirmed",
            "rejected_by_broker",
            "unmatched",
        }:
            raise ValueError("invalid reconciliation status")
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO demo_execution_receipt_reconciliation (
                    readiness_observation_id, position_state_observation_id,
                    reconciliation_status, broker_response_json,
                    reconciliation_json, created_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    readiness_observation_id,
                    position_state_observation_id,
                    reconciliation_status,
                    canonical_json(broker_response),
                    canonical_json(reconciliation),
                    datetime.now(UTC).isoformat(),
                ),
            )
        return cursor.rowcount == 1

    def demo_execution_receipt_reconciliations(
        self, *, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Return immutable broker-receipt reconciliation audit records."""
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM demo_execution_receipt_reconciliation
                ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "readiness_observation_id": str(row["readiness_observation_id"]),
                "position_state_observation_id": str(
                    row["position_state_observation_id"]
                ),
                "status": str(row["reconciliation_status"]),
                "broker_response": json.loads(str(row["broker_response_json"])),
                "reconciliation": json.loads(str(row["reconciliation_json"])),
                "created_at_utc": str(row["created_at_utc"]),
            }
            for row in rows
        ]

    def one_time_demo_readiness(
        self, authorization_scope: str
    ) -> dict[str, Any] | None:
        """Return the single readiness record for the controlled demo scope."""
        with self._lock:
            row = self._connection.execute(
                """
                SELECT * FROM one_time_demo_readiness
                WHERE authorization_scope = ?
                """,
                (authorization_scope,),
            ).fetchone()
        if row is None:
            return None
        return {
            "authorization_scope": str(row["authorization_scope"]),
            "observation_id": str(row["observation_id"]),
            "nonce": str(row["nonce"]),
            "status": str(row["readiness_status"]),
            "checks": json.loads(str(row["checks_json"])),
            "request": json.loads(str(row["request_json"])),
            "account_state": json.loads(str(row["account_state_json"])),
            "created_at_utc": str(row["created_at_utc"]),
        }

    def close(self) -> None:
        with self._lock:
            self._connection.close()
