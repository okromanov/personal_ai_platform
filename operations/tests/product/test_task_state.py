"""Unit tests for the Task State component (ARC_CMP_007).

Runs under the canonical `operations/scripts/quality/run_unittests.py`
discovery, so it is part of the enforced CI gate.
"""

from __future__ import annotations

import unittest

from src.channels import TaskMessage
from src.task_state import InMemoryTaskLifecycleStore


class TaskPersistenceTests(unittest.TestCase):
    def test_saved_task_is_retrievable_by_id(self) -> None:
        store = InMemoryTaskLifecycleStore()
        message = TaskMessage(channel_type="telegram", user_input="hello")

        store.save_task(message)

        self.assertIs(store.load_task(message.task_id), message)

    def test_unknown_task_id_returns_none(self) -> None:
        store = InMemoryTaskLifecycleStore()

        self.assertIsNone(store.load_task("does-not-exist"))

    def test_new_task_has_default_state(self) -> None:
        store = InMemoryTaskLifecycleStore()

        state = store.get_state("never-seen")

        self.assertIsNone(state.checkpoint)
        self.assertEqual(state.retry_count, 0)
        self.assertFalse(state.cancelled)


class CheckpointTests(unittest.TestCase):
    def test_checkpoint_is_retrievable(self) -> None:
        store = InMemoryTaskLifecycleStore()

        store.checkpoint("t1", "tool_called", {"tool": "search", "query": "weather"})

        state = store.get_state("t1")
        assert state.checkpoint is not None
        self.assertEqual(state.checkpoint.step, "tool_called")
        self.assertEqual(state.checkpoint.data, {"tool": "search", "query": "weather"})

    def test_new_checkpoint_replaces_the_previous_one(self) -> None:
        store = InMemoryTaskLifecycleStore()

        store.checkpoint("t1", "planned", {})
        store.checkpoint("t1", "tool_called", {"tool": "search"})

        state = store.get_state("t1")
        assert state.checkpoint is not None
        self.assertEqual(state.checkpoint.step, "tool_called")

    def test_checkpoint_preserves_retry_count_and_cancelled_flag(self) -> None:
        store = InMemoryTaskLifecycleStore()
        store.increment_retry("t1")
        store.cancel("t1")

        store.checkpoint("t1", "tool_called", {})

        state = store.get_state("t1")
        self.assertEqual(state.retry_count, 1)
        self.assertTrue(state.cancelled)


class RetryAndCancelTests(unittest.TestCase):
    def test_increment_retry_increments_and_returns_the_new_count(self) -> None:
        store = InMemoryTaskLifecycleStore()

        self.assertEqual(store.increment_retry("t1"), 1)
        self.assertEqual(store.increment_retry("t1"), 2)
        self.assertEqual(store.get_state("t1").retry_count, 2)

    def test_cancel_marks_state_cancelled(self) -> None:
        store = InMemoryTaskLifecycleStore()

        store.cancel("t1")

        self.assertTrue(store.get_state("t1").cancelled)

    def test_cancelling_twice_is_not_an_error(self) -> None:
        store = InMemoryTaskLifecycleStore()

        store.cancel("t1")
        store.cancel("t1")

        self.assertTrue(store.get_state("t1").cancelled)

    def test_cancel_preserves_checkpoint_and_retry_count(self) -> None:
        store = InMemoryTaskLifecycleStore()
        store.checkpoint("t1", "tool_called", {"tool": "search"})
        store.increment_retry("t1")

        store.cancel("t1")

        state = store.get_state("t1")
        assert state.checkpoint is not None
        self.assertEqual(state.checkpoint.step, "tool_called")
        self.assertEqual(state.retry_count, 1)


class DuplicateProtectionTests(unittest.TestCase):
    def test_distinct_tasks_have_independent_state(self) -> None:
        store = InMemoryTaskLifecycleStore()

        store.checkpoint("t1", "tool_called", {})
        store.increment_retry("t1")
        store.cancel("t1")

        state_t2 = store.get_state("t2")
        self.assertIsNone(state_t2.checkpoint)
        self.assertEqual(state_t2.retry_count, 0)
        self.assertFalse(state_t2.cancelled)


if __name__ == "__main__":
    unittest.main()
