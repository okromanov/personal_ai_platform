"""SQLite implementation of the TaskLifecycleStore contract (INF_CMP_005)."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from src.channels.base import TaskMessage, TaskState
from src.observability import (
    TaskEventResult,
    TaskEventSink,
    TaskEventType,
    emit_task_event,
)

from .base import Checkpoint, TaskLifecycleError, TaskLifecycleState, TaskLifecycleStore


class SQLiteTaskLifecycleStore(TaskLifecycleStore):
    """A durable, single-node TaskLifecycleStore backed by SQLite."""

    def __init__(self, database_path: str | Path, event_sink: TaskEventSink | None = None) -> None:
        if not str(database_path):
            raise ValueError("database_path must not be empty")
        self._database_path = Path(database_path).expanduser()
        self._event_sink = event_sink
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(self._database_path)
            connection.row_factory = sqlite3.Row
            yield connection
            connection.commit()
        except sqlite3.Error as exc:
            if connection is not None:
                connection.rollback()
            raise TaskLifecycleError("SQLite task lifecycle store is unavailable") from exc
        finally:
            if connection is not None:
                connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS task_messages (
                    task_id TEXT PRIMARY KEY,
                    runtime_task_id TEXT NOT NULL DEFAULT '',
                    channel_type TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    error_message TEXT
                );
                CREATE TABLE IF NOT EXISTS task_states (
                    task_id TEXT PRIMARY KEY,
                    checkpoint_step TEXT,
                    checkpoint_data_json TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    cancelled INTEGER NOT NULL DEFAULT 0 CHECK (cancelled IN (0, 1))
                );
                CREATE TABLE IF NOT EXISTS executed_actions (
                    action_id TEXT PRIMARY KEY
                );
                """
            )
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(task_messages)").fetchall()
            }
            if "runtime_task_id" not in columns:
                connection.execute("ALTER TABLE task_messages ADD COLUMN runtime_task_id TEXT")
                connection.execute(
                    "UPDATE task_messages SET runtime_task_id = task_id "
                    "WHERE runtime_task_id IS NULL"
                )

    def _runtime_task_id(self, task_id: str) -> str:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT runtime_task_id FROM task_messages WHERE task_id = ?", (task_id,)
            ).fetchone()
        if row is None or not row[0]:
            return task_id
        return str(row[0])

    def _emit(
        self,
        task_id: str,
        event_type: TaskEventType,
        operation: str,
        *,
        attributes: dict[str, int] | None = None,
    ) -> None:
        emit_task_event(
            self._event_sink,
            runtime_task_id=self._runtime_task_id(task_id),
            event_type=event_type,
            component="task_lifecycle",
            operation=operation,
            result=TaskEventResult.RECORDED,
            attributes=attributes,
        )

    @staticmethod
    def _encode(value: dict[str, Any]) -> str:
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise TaskLifecycleError("Task lifecycle data must be JSON serializable") from exc

    @staticmethod
    def _decode(value: str) -> dict[str, Any]:
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise TaskLifecycleError("Stored task lifecycle data is invalid") from exc
        if not isinstance(decoded, dict):
            raise TaskLifecycleError("Stored task lifecycle data is invalid")
        return decoded

    def save_task(self, message: TaskMessage) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO task_messages (
                    task_id, runtime_task_id, channel_type, user_input, metadata_json, state,
                    created_at, completed_at, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    runtime_task_id = excluded.runtime_task_id,
                    channel_type = excluded.channel_type,
                    user_input = excluded.user_input,
                    metadata_json = excluded.metadata_json,
                    state = excluded.state,
                    created_at = excluded.created_at,
                    completed_at = excluded.completed_at,
                    error_message = excluded.error_message
                """,
                (
                    message.task_id,
                    message.runtime_task_id,
                    message.channel_type,
                    message.user_input,
                    self._encode(message.metadata),
                    message.state.value,
                    message.created_at.isoformat(),
                    message.completed_at.isoformat() if message.completed_at else None,
                    message.error_message,
                ),
            )

    def load_task(self, task_id: str) -> TaskMessage | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM task_messages WHERE task_id = ?", (task_id,)
            ).fetchone()
        if row is None:
            return None
        try:
            completed_at = (
                datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None
            )
            return TaskMessage(
                task_id=row["task_id"],
                runtime_task_id=row["runtime_task_id"],
                channel_type=row["channel_type"],
                user_input=row["user_input"],
                metadata=self._decode(row["metadata_json"]),
                state=TaskState(row["state"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                completed_at=completed_at,
                error_message=row["error_message"],
            )
        except (TypeError, ValueError) as exc:
            raise TaskLifecycleError("Stored task message is invalid") from exc

    def get_state(self, task_id: str) -> TaskLifecycleState:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM task_states WHERE task_id = ?", (task_id,)
            ).fetchone()
        if row is None:
            return TaskLifecycleState()
        checkpoint = None
        if row["checkpoint_step"] is not None:
            data_json = row["checkpoint_data_json"]
            if not isinstance(data_json, str):
                raise TaskLifecycleError("Stored checkpoint is invalid")
            checkpoint = Checkpoint(step=row["checkpoint_step"], data=self._decode(data_json))
        return TaskLifecycleState(
            checkpoint=checkpoint,
            retry_count=int(row["retry_count"]),
            cancelled=bool(row["cancelled"]),
        )

    def checkpoint(self, task_id: str, step: str, data: dict[str, Any]) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO task_states (task_id, checkpoint_step, checkpoint_data_json)
                VALUES (?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    checkpoint_step = excluded.checkpoint_step,
                    checkpoint_data_json = excluded.checkpoint_data_json
                """,
                (task_id, step, self._encode(data)),
            )
        self._emit(task_id, TaskEventType.CHECKPOINT, "save_checkpoint")

    def increment_retry(self, task_id: str) -> int:
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO task_states (task_id) VALUES (?) ON CONFLICT(task_id) DO NOTHING",
                (task_id,),
            )
            connection.execute(
                "UPDATE task_states SET retry_count = retry_count + 1 WHERE task_id = ?",
                (task_id,),
            )
            row = connection.execute(
                "SELECT retry_count FROM task_states WHERE task_id = ?", (task_id,)
            ).fetchone()
        assert row is not None
        retry_count = int(row["retry_count"])
        self._emit(
            task_id,
            TaskEventType.RETRY,
            "increment_retry",
            attributes={"retry_count": retry_count},
        )
        return retry_count

    def cancel(self, task_id: str) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO task_states (task_id, cancelled) VALUES (?, 1)
                ON CONFLICT(task_id) DO UPDATE SET cancelled = 1
                """,
                (task_id,),
            )
        self._emit(task_id, TaskEventType.STATE_TRANSITION, "cancel_task")

    def has_executed(self, action_id: str) -> bool:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT 1 FROM executed_actions WHERE action_id = ?", (action_id,)
            ).fetchone()
        return row is not None

    def mark_executed(self, action_id: str) -> None:
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO executed_actions (action_id) VALUES (?) ON CONFLICT(action_id) DO NOTHING",
                (action_id,),
            )
