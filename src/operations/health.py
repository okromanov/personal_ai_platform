"""Health and observability aggregation (ARC_CMP_009).

Aggregates the health of registered dependencies into one system-wide
report, so a typical failure localizes to a specific dependency instead
of an undifferentiated "something is wrong" (SYS_024). Owns no physical
observability infrastructure (metrics storage, log shipping) -- that
belongs to INF_CMP_007 (TASK_012).
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class DependencyStatus:
    """Health of one named dependency.

    Attributes:
        name: Identifies the dependency (e.g. "task_state", "model_gateway").
        healthy: Whether this dependency is currently working.
        detail: Human-readable reason, especially when unhealthy.
    """

    name: str
    healthy: bool
    detail: str = ""


@dataclass(frozen=True)
class HealthReport:
    """Aggregated health of all registered dependencies.

    Attributes:
        dependencies: One DependencyStatus per registered check.
        generated_at: When this report was produced.
    """

    dependencies: tuple[DependencyStatus, ...]
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def healthy(self) -> bool:
        """Overall health: true only if every dependency is healthy."""
        return all(dependency.healthy for dependency in self.dependencies)

    @property
    def unhealthy_dependencies(self) -> tuple[DependencyStatus, ...]:
        """The subset of dependencies currently failing, for fast localization."""
        return tuple(dependency for dependency in self.dependencies if not dependency.healthy)


HealthCheck = Callable[[], DependencyStatus]


class HealthAggregator:
    """Collects named health checks and aggregates their result.

    A check that raises is treated as an unhealthy result for that one
    dependency rather than aborting the whole report -- one failing
    dependency must not hide the status of the others.
    """

    def __init__(self) -> None:
        self._checks: dict[str, HealthCheck] = {}

    def register(self, name: str, check: HealthCheck) -> None:
        """Register `check` under `name`, replacing any existing check with that name."""
        self._checks[name] = check

    def report(self) -> HealthReport:
        statuses = []
        for name, check in self._checks.items():
            try:
                statuses.append(check())
            except Exception as exc:
                statuses.append(
                    DependencyStatus(name=name, healthy=False, detail=type(exc).__name__)
                )
        return HealthReport(dependencies=tuple(statuses))
