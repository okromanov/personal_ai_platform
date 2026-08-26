"""Reference TaskLifecycleStore implementation (ARC_CMP_007).

An in-process, in-memory store: the minimal working implementation for
m02, same pattern as TASK_002's OwnerControlGate. It does not survive a
process restart -- physical persistence across restarts is provided by
SQLiteTaskLifecycleStore (INF_CMP_005), which connects to this same
contract without changing it.
"""

from typing import Any

from src.channels.base import TaskMessage

from .base import Checkpoint, TaskLifecycleState, TaskLifecycleStore


class InMemoryTaskLifecycleStore(TaskLifecycleStore):
    """Reference `TaskLifecycleStore` backed by process memory."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskMessage] = {}
        self._states: dict[str, TaskLifecycleState] = {}
        self._executed_actions: set[str] = set()

    def save_task(self, message: TaskMessage) -> None:
        self._tasks[message.task_id] = message

    def load_task(self, task_id: str) -> TaskMessage | None:
        return self._tasks.get(task_id)

    def get_state(self, task_id: str) -> TaskLifecycleState:
        return self._states.get(task_id, TaskLifecycleState())

    def checkpoint(self, task_id: str, step: str, data: dict[str, Any]) -> None:
        current = self.get_state(task_id)
        self._states[task_id] = TaskLifecycleState(
            checkpoint=Checkpoint(step=step, data=dict(data)),
            retry_count=current.retry_count,
            cancelled=current.cancelled,
        )

    def increment_retry(self, task_id: str) -> int:
        current = self.get_state(task_id)
        new_count = current.retry_count + 1
        self._states[task_id] = TaskLifecycleState(
            checkpoint=current.checkpoint,
            retry_count=new_count,
            cancelled=current.cancelled,
        )
        return new_count

    def cancel(self, task_id: str) -> None:
        current = self.get_state(task_id)
        self._states[task_id] = TaskLifecycleState(
            checkpoint=current.checkpoint,
            retry_count=current.retry_count,
            cancelled=True,
        )

    def has_executed(self, action_id: str) -> bool:
        return action_id in self._executed_actions

    def mark_executed(self, action_id: str) -> None:
        self._executed_actions.add(action_id)
