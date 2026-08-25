"""Task lifecycle store abstraction (ARC_CMP_007).

Persists the identity and execution lifecycle of one task -- current
checkpoint, retry count, and cancellation -- independent of any concrete
agent execution environment (`RuntimePort`, ARC_CMP_003). This state must
survive an orchestrator restart, so it is explicitly not internal state
of whichever `RuntimePort` implementation happens to be connected.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.channels.base import TaskMessage


class TaskLifecycleError(Exception):
    """Raised when the store itself cannot be reached (unavailable, corrupted)."""


@dataclass(frozen=True)
class Checkpoint:
    """A resumable point in a task's execution.

    Attributes:
        step: Caller-defined label for the point reached (e.g. "planned",
            "tool_called", "awaiting_confirmation").
        data: Enough state for the caller to resume from this exact point.
    """

    step: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskLifecycleState:
    """Everything the store tracks for one task, beyond the task message itself.

    Attributes:
        checkpoint: The most recent resumable point, or None if execution
            has not reached one yet.
        retry_count: Number of times execution has been retried.
        cancelled: Whether the task has been cancelled.
    """

    checkpoint: Checkpoint | None = None
    retry_count: int = 0
    cancelled: bool = False


class TaskLifecycleStore(ABC):
    """Abstract contract for persisting a task's identity and execution lifecycle.

    Implementations own the physical storage (in-memory, file, database).
    Swapping the implementation must not require changes to the
    orchestrator or any other component above this boundary.
    """

    @abstractmethod
    def save_task(self, message: TaskMessage) -> None:
        """Persist (or overwrite) the task message itself, keyed by its task_id."""

    @abstractmethod
    def load_task(self, task_id: str) -> TaskMessage | None:
        """Return the persisted task message, or None if task_id is unknown."""

    @abstractmethod
    def get_state(self, task_id: str) -> TaskLifecycleState:
        """Return the current lifecycle state for task_id.

        Returns the default state (no checkpoint, zero retries, not
        cancelled) for a task_id the store has never seen a checkpoint,
        retry, or cancellation for.
        """

    @abstractmethod
    def checkpoint(self, task_id: str, step: str, data: dict[str, Any]) -> None:
        """Record a resumable checkpoint for task_id, replacing any previous one."""

    @abstractmethod
    def increment_retry(self, task_id: str) -> int:
        """Increment and return the retry count for task_id."""

    @abstractmethod
    def cancel(self, task_id: str) -> None:
        """Mark task_id cancelled. Idempotent: cancelling twice is not an error."""

    @abstractmethod
    def has_executed(self, action_id: str) -> bool:
        """Whether action_id was already recorded as executed (duplicate protection)."""

    @abstractmethod
    def mark_executed(self, action_id: str) -> None:
        """Record action_id as executed, so a retry does not repeat its effect."""
