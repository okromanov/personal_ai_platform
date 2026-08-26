"""Tests for durable SQLite TaskLifecycleStore (INF_CMP_005)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.channels import TaskMessage, TaskState
from src.task_state import SQLiteTaskLifecycleStore


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
            first.mark_executed("send-message:task-1")

            restored = SQLiteTaskLifecycleStore(database_path)
            loaded_message = restored.load_task("task-1")
            state = restored.get_state("task-1")

            assert loaded_message is not None
            self.assertEqual(loaded_message.channel_type, "telegram")
            self.assertEqual(loaded_message.user_input, "prepare report")
            self.assertEqual(loaded_message.metadata, {"user_id": "42"})
            self.assertEqual(loaded_message.state, TaskState.RUNNING)
            assert state.checkpoint is not None
            self.assertEqual(state.checkpoint.step, "tool_called")
            self.assertEqual(state.checkpoint.data, {"tool": "search"})
            self.assertEqual(state.retry_count, 1)
            self.assertTrue(state.cancelled)
            self.assertTrue(restored.has_executed("send-message:task-1"))

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


if __name__ == "__main__":
    unittest.main()
