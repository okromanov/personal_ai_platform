"""Tests for privacy-preserving infrastructure observability (INF_CMP_007)."""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from src.observability import (
    ObservabilityCollector,
    ObservationEvent,
    ObservationKind,
    ResourceUsage,
    SQLiteObservabilityStore,
)
from src.operations import DependencyStatus, HealthReport


class ObservabilityTests(unittest.TestCase):
    def _store(self) -> SQLiteObservabilityStore:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        return SQLiteObservabilityStore(Path(directory.name) / "observability.sqlite3")

    def test_health_report_is_localized_without_storing_failure_detail(self) -> None:
        store = self._store()
        collector = ObservabilityCollector(store)
        collector.record_health(
            HealthReport(
                dependencies=(
                    DependencyStatus(name="task_state", healthy=True),
                    DependencyStatus(
                        name="model_gateway",
                        healthy=False,
                        detail="prompt text must not be recorded",
                    ),
                ),
                generated_at=datetime(2026, 8, 26, tzinfo=UTC),
            )
        )
        events = store.list_events()
        self.assertEqual([event.component for event in events], ["task_state", "model_gateway"])
        self.assertEqual(events[1].measurements, {"healthy": False})
        self.assertNotIn("prompt", str(events))

    def test_resource_and_external_usage_are_persisted_across_store_instances(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "observability.sqlite3"
            collector = ObservabilityCollector(SQLiteObservabilityStore(database_path))
            collector.record_resources(
                ResourceUsage("runtime", cpu_seconds=1.25, memory_bytes=2048)
            )
            collector.record_external_usage(
                "model_gateway", request_units=3, response_units=5, cost_microunits=42
            )
            events = SQLiteObservabilityStore(database_path).list_events()
        self.assertEqual(events[0].kind, ObservationKind.RESOURCE_USAGE)
        self.assertEqual(events[0].measurements["memory_bytes"], 2048)
        self.assertEqual(events[1].kind, ObservationKind.EXTERNAL_USAGE)
        self.assertEqual(events[1].measurements["cost_microunits"], 42)

    def test_free_text_measurements_are_rejected(self) -> None:
        with self.assertRaises(TypeError):
            ObservationEvent(
                kind=ObservationKind.TECHNICAL_EVENT,
                component="model_gateway",
                measurements={"detail": "user message"},  # type: ignore[dict-item]
            )

    def test_negative_usage_is_rejected(self) -> None:
        collector = ObservabilityCollector(self._store())
        with self.assertRaises(ValueError):
            collector.record_external_usage(
                "model_gateway", request_units=-1, response_units=0, cost_microunits=0
            )
        with self.assertRaises(ValueError):
            ResourceUsage("runtime", cpu_seconds=0, memory_bytes=-1)

    def test_technical_event_uses_a_numeric_code_only(self) -> None:
        store = self._store()
        collector = ObservabilityCollector(store)
        collector.record_technical_event("network_policy", event_code=1001)
        self.assertEqual(store.list_events()[0].measurements, {"event_code": 1001})


if __name__ == "__main__":
    unittest.main()
