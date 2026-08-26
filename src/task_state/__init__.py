"""Task state: identity and execution lifecycle of a task, across restarts.

Provides a stable contract (TaskLifecycleStore) for persisting a task
message and its execution state -- checkpoint, retry count, cancellation,
and duplicate-action protection -- independent of any concrete agent
execution environment. Includes an in-memory reference implementation,
the minimal working option for m02; physical persistence across process
restarts (INF_CMP_005) connects to this same contract later.

This module implements ARC_CMP_007 — Состояние задач (Task State).
"""

from .base import Checkpoint, TaskLifecycleError, TaskLifecycleState, TaskLifecycleStore
from .sqlite_store import SQLiteTaskLifecycleStore
from .store import InMemoryTaskLifecycleStore

__all__ = [
    "Checkpoint",
    "InMemoryTaskLifecycleStore",
    "SQLiteTaskLifecycleStore",
    "TaskLifecycleError",
    "TaskLifecycleState",
    "TaskLifecycleStore",
]
