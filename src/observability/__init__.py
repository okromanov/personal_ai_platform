"""Privacy-preserving operational observations (INF_CMP_007)."""

# ruff: noqa: I001 -- task_events must initialize before collector; see below.

# Import the dependency-free event contract first. collector imports the
# operations package, whose scheduler imports task_state; task_state may use
# this contract without depending on the heavier collector initialization.
from .task_events import (
    InMemoryTaskEventSink,
    TaskEvent,
    TaskEventResult,
    TaskEventSink,
    TaskEventType,
    emit_task_event,
)
from .collector import (
    ObservabilityCollector,
    ObservationEvent,
    ObservationKind,
    ResourceUsage,
)
from .sqlite_store import SQLiteObservabilityStore

__all__ = [
    "ObservationEvent",
    "ObservationKind",
    "ObservabilityCollector",
    "ResourceUsage",
    "SQLiteObservabilityStore",
    "InMemoryTaskEventSink",
    "TaskEvent",
    "TaskEventResult",
    "TaskEventSink",
    "TaskEventType",
    "emit_task_event",
]
