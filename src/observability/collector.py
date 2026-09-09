"""Collect privacy-preserving health, resource and usage observations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping, Protocol

from src.operations.health import HealthReport


class ObservationKind(StrEnum):
    """The finite set of technical observations retained by the platform."""

    DEPENDENCY_HEALTH = "dependency_health"
    RESOURCE_USAGE = "resource_usage"
    EXTERNAL_USAGE = "external_usage"
    TECHNICAL_EVENT = "technical_event"


TechnicalValue = int | float | bool


@dataclass(frozen=True)
class ObservationEvent:
    """One sanitized, timestamped technical fact."""

    kind: ObservationKind
    component: str
    measurements: Mapping[str, TechnicalValue] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.component or not self.component.replace("_", "").isalnum():
            raise ValueError("component must be a non-empty technical identifier")
        for name, value in self.measurements.items():
            if not name or not name.replace("_", "").isalnum():
                raise ValueError("measurement names must be technical identifiers")
            if not isinstance(value, (int, float, bool)):
                raise TypeError("measurements may contain only numbers or booleans")
        object.__setattr__(self, "measurements", MappingProxyType(dict(self.measurements)))


@dataclass(frozen=True)
class ResourceUsage:
    """Measured resources of a component at one point in time."""

    component: str
    cpu_seconds: float
    memory_bytes: int

    def __post_init__(self) -> None:
        if self.cpu_seconds < 0 or self.memory_bytes < 0:
            raise ValueError("resource usage cannot be negative")


class ObservationSink(Protocol):
    """Persistent destination for sanitized observations."""

    def append(self, event: ObservationEvent) -> None: ...


class ObservabilityCollector:
    """Turns health reports and measured usage into sanitized observations."""

    def __init__(self, sink: ObservationSink) -> None:
        self._sink = sink

    def record_health(self, report: HealthReport) -> None:
        """Persist one health result per dependency, without its free-text detail."""
        for dependency in report.dependencies:
            self._sink.append(
                ObservationEvent(
                    kind=ObservationKind.DEPENDENCY_HEALTH,
                    component=dependency.name,
                    measurements={"healthy": dependency.healthy},
                    occurred_at=report.generated_at,
                )
            )

    def record_resources(self, usage: ResourceUsage) -> None:
        """Persist a resource measurement supplied by the runtime environment."""
        self._sink.append(
            ObservationEvent(
                kind=ObservationKind.RESOURCE_USAGE,
                component=usage.component,
                measurements={
                    "cpu_seconds": usage.cpu_seconds,
                    "memory_bytes": usage.memory_bytes,
                },
            )
        )

    def record_external_usage(
        self, component: str, *, request_units: int, response_units: int, cost_microunits: int
    ) -> None:
        """Persist countable provider consumption, never request or response text."""
        if min(request_units, response_units, cost_microunits) < 0:
            raise ValueError("external usage cannot be negative")
        self._sink.append(
            ObservationEvent(
                kind=ObservationKind.EXTERNAL_USAGE,
                component=component,
                measurements={
                    "request_units": request_units,
                    "response_units": response_units,
                    "cost_microunits": cost_microunits,
                },
            )
        )

    def record_technical_event(self, component: str, event_code: int) -> None:
        """Persist a numeric event code, not a message or exception string."""
        if event_code < 0:
            raise ValueError("event_code cannot be negative")
        self._sink.append(
            ObservationEvent(
                kind=ObservationKind.TECHNICAL_EVENT,
                component=component,
                measurements={"event_code": event_code},
            )
        )
