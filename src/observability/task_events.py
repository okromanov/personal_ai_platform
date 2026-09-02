"""Privacy-safe structured events for one runtime task (ADR_004)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Mapping, Protocol


class TaskEventType(StrEnum):
    """Portable event categories required by the runtime event contract."""

    STATE_TRANSITION = "state_transition"
    MODEL_CALL = "model_call"
    TOOL_CALL = "tool_call"
    POLICY_DECISION = "policy_decision"
    CHECKPOINT = "checkpoint"
    RETRY = "retry"
    ERROR = "error"


class TaskEventResult(StrEnum):
    """Normalized outcomes; exception messages and payloads are never results."""

    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ALLOWED = "allowed"
    DENIED = "denied"
    RECORDED = "recorded"
    CANCELLED = "cancelled"


SafeAttributeValue = int | float | bool
_TECHNICAL_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")


def _technical_identifier(value: str, field_name: str) -> None:
    if _TECHNICAL_IDENTIFIER.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a non-empty technical identifier")


@dataclass(frozen=True)
class TaskEvent:
    """One correlated event containing only bounded technical metadata."""

    runtime_task_id: str
    event_type: TaskEventType
    component: str
    operation: str
    result: TaskEventResult
    attributes: Mapping[str, SafeAttributeValue] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    trace_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None

    def __post_init__(self) -> None:
        _technical_identifier(self.runtime_task_id, "runtime_task_id")
        _technical_identifier(self.component, "component")
        _technical_identifier(self.operation, "operation")
        for name, value in self.attributes.items():
            _technical_identifier(name, "attribute name")
            if not isinstance(value, (int, float, bool)):
                raise TypeError("event attributes may contain only numbers or booleans")
        for field_name, trace_value in (
            ("trace_id", self.trace_id),
            ("span_id", self.span_id),
            ("parent_span_id", self.parent_span_id),
        ):
            if trace_value is not None:
                _technical_identifier(trace_value, field_name)


class TaskEventSink(Protocol):
    """Destination for sanitized task events."""

    def append(self, event: TaskEvent) -> None: ...


class InMemoryTaskEventSink:
    """Deterministic reference sink used by local runtimes and tests."""

    def __init__(self) -> None:
        self._events: list[TaskEvent] = []

    def append(self, event: TaskEvent) -> None:
        self._events.append(event)

    def list_events(self, runtime_task_id: str | None = None) -> tuple[TaskEvent, ...]:
        if runtime_task_id is None:
            return tuple(self._events)
        return tuple(event for event in self._events if event.runtime_task_id == runtime_task_id)


def emit_task_event(
    sink: TaskEventSink | None,
    *,
    runtime_task_id: str,
    event_type: TaskEventType,
    component: str,
    operation: str,
    result: TaskEventResult,
    attributes: Mapping[str, SafeAttributeValue] | None = None,
) -> None:
    """Append a validated event when an event destination is configured."""
    if sink is None:
        return
    sink.append(
        TaskEvent(
            runtime_task_id=runtime_task_id,
            event_type=event_type,
            component=component,
            operation=operation,
            result=result,
            attributes=attributes or {},
        )
    )
