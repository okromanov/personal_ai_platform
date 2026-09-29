"""Tests for durable SQLite TaskLifecycleStore (INF_CMP_005)."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.channels import TaskMessage, TaskState
from src.task_state import SQLiteTaskLifecycleStore, TaskLifecycleError


class SQLiteTaskLifecycleStoreTests(unittest.TestCase):
    def test_state_and_message_survive_new_store_instance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "task-state.sqlite3"
            first = SQLiteTaskLifecycleStore(database_path)
            message = TaskMessage(
                task_id="task-1",
                channel_type="telegram",
                user_input="prepare report",
                metadata={"user_id": "42"},
            )
            message.mark_running()
            first.save_task(message)
            first.checkpoint("task-1", "tool_called", {"tool": "search"})
            self.assertEqual(first.increment_retry("task-1"), 1)
            first.cancel("task-1")

            restored = SQLiteTaskLifecycleStore(database_path)
            loaded_message = restored.load_task("task-1")
            state = restored.get_state("task-1")

            assert loaded_message is not None
            self.assertEqual(loaded_message.runtime_task_id, message.runtime_task_id)
            self.assertEqual(loaded_message.channel_type, "telegram")
            self.assertEqual(loaded_message.user_input, "prepare report")
            self.assertEqual(loaded_message.metadata, {"user_id": "42"})
            self.assertEqual(loaded_message.state, TaskState.RUNNING)
            assert state.checkpoint is not None
            self.assertEqual(state.checkpoint.step, "tool_called")
            self.assertEqual(state.checkpoint.data, {"tool": "search"})
            self.assertEqual(state.retry_count, 1)
            self.assertTrue(state.cancelled)

    def test_unknown_task_keeps_default_state_after_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "task-state.sqlite3"
            SQLiteTaskLifecycleStore(database_path)

            restored = SQLiteTaskLifecycleStore(database_path)

            self.assertIsNone(restored.load_task("unknown"))
            self.assertEqual(restored.get_state("unknown").retry_count, 0)

    def test_replacing_checkpoint_keeps_other_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteTaskLifecycleStore(Path(directory) / "task-state.sqlite3")
            store.increment_retry("task-1")
            store.cancel("task-1")
            store.checkpoint("task-1", "first", {})
            store.checkpoint("task-1", "second", {"value": 2})

            state = store.get_state("task-1")

            assert state.checkpoint is not None
            self.assertEqual(state.checkpoint.step, "second")
            self.assertEqual(state.retry_count, 1)
            self.assertTrue(state.cancelled)


class SQLiteTaskLifecycleStoreCorruptionTests(unittest.TestCase):
    """AUD-019: these decode/state-validation paths (mirroring
    test_owner_control.py's coverage of the same JSON-in-storage-corruption
    risk class) were never exercised -- write directly to the database,
    bypassing the store's own encode(), to simulate real corruption."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.database_path = Path(self._tmp.name) / "task-state.sqlite3"
        self.store = SQLiteTaskLifecycleStore(self.database_path)

    def _insert_task_message(self, *, metadata_json: str, state: str) -> None:
        # sqlite3.Connection's context manager only commits/rolls back the
        # transaction on exit -- it does not close the connection. An
        # unclosed connection keeps the database file open, which is a
        # silent no-op on POSIX but a PermissionError on Windows when the
        # enclosing TemporaryDirectory tries to delete it during teardown.
        connection = sqlite3.connect(self.database_path)
        try:
            with connection:
                connection.execute(
                    """
                    INSERT INTO task_messages (
                        task_id, channel_type, user_input, metadata_json, state,
                        created_at, completed_at, error_message
                    ) VALUES ('task-1', 'telegram', 'hi', ?, ?, '2026-08-29T00:00:00', NULL, NULL)
                    """,
                    (metadata_json, state),
                )
        finally:
            connection.close()

    def test_load_task_with_invalid_metadata_json_fails_closed(self) -> None:
        self._insert_task_message(metadata_json="not json", state=TaskState.PENDING.value)
        with self.assertRaises(TaskLifecycleError):
            self.store.load_task("task-1")

    def test_load_task_with_non_dict_metadata_json_fails_closed(self) -> None:
        self._insert_task_message(metadata_json="[1, 2, 3]", state=TaskState.PENDING.value)
        with self.assertRaises(TaskLifecycleError):
            self.store.load_task("task-1")

    def test_load_task_with_unknown_state_fails_closed(self) -> None:
        self._insert_task_message(metadata_json="{}", state="not_a_real_state")
        with self.assertRaises(TaskLifecycleError):
            self.store.load_task("task-1")

    def test_get_state_with_invalid_checkpoint_data_json_fails_closed(self) -> None:
        connection = sqlite3.connect(self.database_path)
        try:
            with connection:
                connection.execute(
                    """
                    INSERT INTO task_states (task_id, checkpoint_step, checkpoint_data_json)
                    VALUES ('task-1', 'tool_called', 'not json')
                    """
                )
        finally:
            connection.close()
        with self.assertRaises(TaskLifecycleError):
            self.store.get_state("task-1")

    def test_get_state_with_non_dict_checkpoint_data_json_fails_closed(self) -> None:
        connection = sqlite3.connect(self.database_path)
        try:
            with connection:
                connection.execute(
                    """
                    INSERT INTO task_states (task_id, checkpoint_step, checkpoint_data_json)
                    VALUES ('task-1', 'tool_called', '"just a string"')
                    """
                )
        finally:
            connection.close()
        with self.assertRaises(TaskLifecycleError):
            self.store.get_state("task-1")


if __name__ == "__main__":
    unittest.main()
