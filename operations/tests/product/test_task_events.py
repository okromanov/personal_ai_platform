"""Tests for correlated, privacy-safe runtime task events (ADR_004)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.channels import TaskMessage, TelegramChannel
from src.models import ModelBackedRuntimePort, StubModelGateway
from src.observability import (
    InMemoryTaskEventSink,
    TaskEvent,
    TaskEventResult,
    TaskEventType,
)
from src.orchestration import Orchestrator
from src.owner_control import ActionClass, OwnerControlGate
from src.task_state import InMemoryTaskLifecycleStore
from src.tools import Capability, ToolCall, ToolGatewayImpl


class RuntimeTaskEventTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.gate = OwnerControlGate("owner_1", Path(self.tmp.name))

    async def test_execution_components_share_one_runtime_task_id(self) -> None:
        sentinel = "SENSITIVE_SENTINEL_NEVER_STORE"
        sink = InMemoryTaskEventSink()
        message = TaskMessage(user_input=sentinel)
        gateway = StubModelGateway()
        runtime = ModelBackedRuntimePort(gateway, event_sink=sink)
        orchestrator = Orchestrator(self.gate, runtime, event_sink=sink)

        await orchestrator.handle(
            message,
            subject_id="owner_1",
            channel=TelegramChannel(bot_token="test_token"),
        )

        lifecycle = InMemoryTaskLifecycleStore(event_sink=sink)
        lifecycle.save_task(message)
        lifecycle.checkpoint(message.task_id, sentinel, {"payload": sentinel})
        lifecycle.increment_retry(message.task_id)

        async def handler(_call: ToolCall) -> str:
            return sentinel

        tool_gateway = ToolGatewayImpl(
            self.gate,
            [
                Capability(
                    name="read_note",
                    effect_class=ActionClass.READ,
                    handler=handler,
                    allowed_subjects=frozenset({"owner_1"}),
                    allowed_param_names=frozenset({"secret"}),
                )
            ],
            event_sink=sink,
        )
        tool_result = await tool_gateway.call(
            ToolCall(
                action_id="read_1",
                subject_id="owner_1",
                capability_name="read_note",
                resource=sentinel,
                params={"secret": sentinel},
                runtime_task_id=message.runtime_task_id,
            )
        )

        self.assertTrue(tool_result.succeeded)
        events = sink.list_events(message.runtime_task_id)
        event_types = {event.event_type for event in events}
        self.assertTrue(
            {
                TaskEventType.STATE_TRANSITION,
                TaskEventType.MODEL_CALL,
                TaskEventType.TOOL_CALL,
                TaskEventType.POLICY_DECISION,
                TaskEventType.CHECKPOINT,
                TaskEventType.RETRY,
            }.issubset(event_types)
        )
        self.assertTrue(events)
        self.assertEqual({event.runtime_task_id for event in events}, {message.runtime_task_id})
        self.assertNotIn(sentinel, repr(events))

    async def test_normalized_error_event_excludes_provider_detail(self) -> None:
        sentinel = "provider_secret_error"
        sink = InMemoryTaskEventSink()
        gateway = StubModelGateway()
        gateway.register_failure("fail", sentinel)
        message = TaskMessage(user_input="fail")
        orchestrator = Orchestrator(
            self.gate,
            ModelBackedRuntimePort(gateway, event_sink=sink),
            event_sink=sink,
        )

        await orchestrator.handle(
            message,
            subject_id="owner_1",
            channel=TelegramChannel(bot_token="test_token"),
        )

        events = sink.list_events(message.runtime_task_id)
        self.assertIn(TaskEventType.ERROR, {event.event_type for event in events})
        self.assertNotIn(sentinel, repr(events))

    async def test_distinct_executions_do_not_mix(self) -> None:
        sink = InMemoryTaskEventSink()
        orchestrator = Orchestrator(
            self.gate,
            ModelBackedRuntimePort(StubModelGateway(), event_sink=sink),
            event_sink=sink,
        )
        first = TaskMessage(user_input="first")
        second = TaskMessage(user_input="second")
        channel = TelegramChannel(bot_token="test_token")

        await orchestrator.handle(first, subject_id="owner_1", channel=channel)
        await orchestrator.handle(second, subject_id="owner_1", channel=channel)

        self.assertNotEqual(first.runtime_task_id, second.runtime_task_id)
        first_events = sink.list_events(first.runtime_task_id)
        second_events = sink.list_events(second.runtime_task_id)
        self.assertTrue(first_events)
        self.assertTrue(second_events)
        self.assertTrue(
            all(event.runtime_task_id == first.runtime_task_id for event in first_events)
        )
        self.assertTrue(
            all(event.runtime_task_id == second.runtime_task_id for event in second_events)
        )


class TaskEventSchemaTests(unittest.TestCase):
    def test_free_text_attribute_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            TaskEvent(
                runtime_task_id="runtime_1",
                event_type=TaskEventType.ERROR,
                component="runtime",
                operation="execute",
                result=TaskEventResult.FAILED,
                attributes={"detail": "user content"},  # type: ignore[dict-item]
            )


if __name__ == "__main__":
    unittest.main()
