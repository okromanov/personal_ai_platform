"""Unit tests for the Operational Functions component (ARC_CMP_009).

Runs under the canonical `operations/scripts/quality/run_unittests.py`
discovery, so it is part of the enforced CI gate.
"""

from __future__ import annotations

import unittest

from src.operations import DependencyStatus, HealthAggregator, ScheduledIntent, SchedulerState
from src.task_state import InMemoryTaskLifecycleStore


class HealthAggregatorTests(unittest.TestCase):
    def test_report_is_healthy_when_every_check_is_healthy(self) -> None:
        aggregator = HealthAggregator()
        aggregator.register("task_state", lambda: DependencyStatus(name="task_state", healthy=True))
        aggregator.register(
            "model_gateway", lambda: DependencyStatus(name="model_gateway", healthy=True)
        )

        report = aggregator.report()

        self.assertTrue(report.healthy)
        self.assertEqual(len(report.dependencies), 2)

    def test_report_is_unhealthy_when_any_check_fails(self) -> None:
        aggregator = HealthAggregator()
        aggregator.register("task_state", lambda: DependencyStatus(name="task_state", healthy=True))
        aggregator.register(
            "model_gateway",
            lambda: DependencyStatus(name="model_gateway", healthy=False, detail="timeout"),
        )

        report = aggregator.report()

        self.assertFalse(report.healthy)

    def test_unhealthy_dependencies_localizes_to_the_failing_ones_only(self) -> None:
        aggregator = HealthAggregator()
        aggregator.register("task_state", lambda: DependencyStatus(name="task_state", healthy=True))
        aggregator.register(
            "model_gateway",
            lambda: DependencyStatus(name="model_gateway", healthy=False, detail="timeout"),
        )

        report = aggregator.report()

        self.assertEqual(len(report.unhealthy_dependencies), 1)
        self.assertEqual(report.unhealthy_dependencies[0].name, "model_gateway")
        self.assertEqual(report.unhealthy_dependencies[0].detail, "timeout")

    def test_a_raising_check_is_isolated_as_that_dependencys_failure(self) -> None:
        def _boom() -> DependencyStatus:
            raise RuntimeError("dependency crashed")

        aggregator = HealthAggregator()
        aggregator.register("ok", lambda: DependencyStatus(name="ok", healthy=True))
        aggregator.register("crashing", _boom)

        report = aggregator.report()

        self.assertFalse(report.healthy)
        self.assertEqual(len(report.dependencies), 2)
        crashing = next(d for d in report.dependencies if d.name == "crashing")
        self.assertFalse(crashing.healthy)
        self.assertEqual(crashing.detail, "RuntimeError")

    def test_registering_the_same_name_twice_replaces_the_check(self) -> None:
        aggregator = HealthAggregator()
        aggregator.register("x", lambda: DependencyStatus(name="x", healthy=False))
        aggregator.register("x", lambda: DependencyStatus(name="x", healthy=True))

        report = aggregator.report()

        self.assertEqual(len(report.dependencies), 1)
        self.assertTrue(report.dependencies[0].healthy)


class SchedulerStateTests(unittest.TestCase):
    def test_new_scheduler_is_not_paused(self) -> None:
        scheduler = SchedulerState()

        self.assertFalse(scheduler.paused)

    def test_active_task_intent_is_runnable(self) -> None:
        scheduler = SchedulerState()
        store = InMemoryTaskLifecycleStore()
        scheduler.register_intent(
            ScheduledIntent(intent_id="i1", capability_name="send", task_id="t1")
        )

        runnable = scheduler.runnable_intents(store)

        self.assertEqual([intent.intent_id for intent in runnable], ["i1"])

    def test_cancelled_task_intent_is_not_runnable(self) -> None:
        scheduler = SchedulerState()
        store = InMemoryTaskLifecycleStore()
        store.cancel("t1")
        scheduler.register_intent(
            ScheduledIntent(intent_id="i1", capability_name="send", task_id="t1")
        )

        self.assertEqual(scheduler.runnable_intents(store), [])

    def test_pause_stops_all_intents_regardless_of_task_state(self) -> None:
        scheduler = SchedulerState()
        store = InMemoryTaskLifecycleStore()
        scheduler.register_intent(
            ScheduledIntent(intent_id="i1", capability_name="send", task_id="t1")
        )

        scheduler.pause()

        self.assertTrue(scheduler.paused)
        self.assertEqual(scheduler.runnable_intents(store), [])

    def test_resume_restores_runnable_intents(self) -> None:
        scheduler = SchedulerState()
        store = InMemoryTaskLifecycleStore()
        scheduler.register_intent(
            ScheduledIntent(intent_id="i1", capability_name="send", task_id="t1")
        )
        scheduler.pause()

        scheduler.resume()

        self.assertFalse(scheduler.paused)
        self.assertEqual([intent.intent_id for intent in scheduler.runnable_intents(store)], ["i1"])

    def test_multiple_intents_are_filtered_independently_by_task_state(self) -> None:
        scheduler = SchedulerState()
        store = InMemoryTaskLifecycleStore()
        store.cancel("t2")
        scheduler.register_intent(
            ScheduledIntent(intent_id="i1", capability_name="send", task_id="t1")
        )
        scheduler.register_intent(
            ScheduledIntent(intent_id="i2", capability_name="send", task_id="t2")
        )

        runnable_ids = {intent.intent_id for intent in scheduler.runnable_intents(store)}

        self.assertEqual(runnable_ids, {"i1"})

    def test_registering_the_same_intent_id_twice_replaces_it(self) -> None:
        scheduler = SchedulerState()
        store = InMemoryTaskLifecycleStore()
        scheduler.register_intent(
            ScheduledIntent(intent_id="i1", capability_name="send", task_id="t1")
        )
        scheduler.register_intent(
            ScheduledIntent(intent_id="i1", capability_name="delete", task_id="t2")
        )

        runnable = scheduler.runnable_intents(store)

        self.assertEqual(len(runnable), 1)
        self.assertEqual(runnable[0].capability_name, "delete")
        self.assertEqual(runnable[0].task_id, "t2")


if __name__ == "__main__":
    unittest.main()
