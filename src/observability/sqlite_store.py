"""Portable SQLite persistence for sanitized observability events."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .collector import ObservationEvent, ObservationKind, TechnicalValue


class SQLiteObservabilityStore:
    """Append-only local storage for operational observations in the m02 baseline."""

    def __init__(self, database_path: str | Path) -> None:
        if not str(database_path):
            raise ValueError("database_path must not be empty")
        self._database_path = Path(database_path).expanduser()
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._database_path)
        try:
            yield connection
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise RuntimeError("observability store is unavailable") from exc
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS observation_events (
                    id INTEGER PRIMARY KEY,
                    kind TEXT NOT NULL,
                    component TEXT NOT NULL,
                    measurements_json TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                )
                """
            )

    def append(self, event: ObservationEvent) -> None:
        measurements = json.dumps(dict(event.measurements), sort_keys=True)
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO observation_events (kind, component, measurements_json, occurred_at)
                VALUES (?, ?, ?, ?)
                """,
                (event.kind.value, event.component, measurements, event.occurred_at.isoformat()),
            )

    def list_events(self) -> tuple[ObservationEvent, ...]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT kind, component, measurements_json, occurred_at
                FROM observation_events ORDER BY id
                """
            ).fetchall()
        return tuple(self._decode(row) for row in rows)

    @staticmethod
    def _decode(row: tuple[str, str, str, str]) -> ObservationEvent:
        kind, component, measurements_json, occurred_at = row
        try:
            decoded = json.loads(measurements_json)
            if not isinstance(decoded, dict) or not all(
                isinstance(value, (int, float, bool)) for value in decoded.values()
            ):
                raise ValueError
            measurements: dict[str, TechnicalValue] = decoded
            return ObservationEvent(
                kind=ObservationKind(kind),
                component=component,
                measurements=measurements,
                occurred_at=datetime.fromisoformat(occurred_at),
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError("stored observation is invalid") from exc
