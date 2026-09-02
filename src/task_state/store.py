"""Reference TaskLifecycleStore implementation (ARC_CMP_007).

An in-process, in-memory store: the minimal working implementation for
m02, same pattern as TASK_002's OwnerControlGate. It does not survive a
process restart -- physical persistence across restarts is provided by
SQLiteTaskLifecycleStore (INF_CMP_005), which connects to this same
contract without changing it.
"""

from typing import Any

from src.channels.base import TaskMessage
from src.observability import (
    TaskEventResult,
    TaskEventSink,
    TaskEventType,
    emit_task_event,
)

from .base import Checkpoint, TaskLifecycleState, TaskLifecycleStore


class InMemoryTaskLifecycleStore(TaskLifecycleStore):
    """Reference `TaskLifecycleStore` backed by process memory."""

    def __init__(self, event_sink: TaskEventSink | None = None) -> None:
        self._tasks: dict[str, TaskMessage] = {}
        self._states: dict[str, TaskLifecycleState] = {}
        self._executed_actions: set[str] = set()
        self._event_sink = event_sink

    def _runtime_task_id(self, task_id: str) -> str:
        message = self._tasks.get(task_id)
        return message.runtime_task_id if message is not None else task_id

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
        self._emit(task_id, TaskEventType.CHECKPOINT, "save_checkpoint")

    def increment_retry(self, task_id: str) -> int:
        current = self.get_state(task_id)
        new_count = current.retry_count + 1
        self._states[task_id] = TaskLifecycleState(
            checkpoint=current.checkpoint,
            retry_count=new_count,
            cancelled=current.cancelled,
        )
        self._emit(
            task_id,
            TaskEventType.RETRY,
            "increment_retry",
            attributes={"retry_count": new_count},
        )
        return new_count

    def cancel(self, task_id: str) -> None:
        current = self.get_state(task_id)
        self._states[task_id] = TaskLifecycleState(
            checkpoint=current.checkpoint,
            retry_count=current.retry_count,
            cancelled=True,
        )
        self._emit(task_id, TaskEventType.STATE_TRANSITION, "cancel_task")

    def has_executed(self, action_id: str) -> bool:
        return action_id in self._executed_actions

    def mark_executed(self, action_id: str) -> None:
        self._executed_actions.add(action_id)
