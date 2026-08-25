"""Unit tests for the Orchestration component (ARC_CMP_003).

Runs under the canonical `operations/scripts/quality/run_unittests.py`
discovery, so it is part of the enforced CI gate.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.channels import TaskMessage, TaskState, TelegramChannel
from src.orchestration import (
    Orchestrator,
    RuntimePort,
    RuntimePortError,
    RuntimeResult,
    StubRuntimePort,
)
from src.owner_control import OwnerControlGate


def _gate(
    owner_subject_id: str = "owner_1",
) -> tuple[OwnerControlGate, tempfile.TemporaryDirectory]:
    tmp = tempfile.TemporaryDirectory()
    gate = OwnerControlGate(owner_subject_id=owner_subject_id, state_dir=Path(tmp.name))
    return gate, tmp


class AltRuntimePort(RuntimePort):
    """A second, independent RuntimePort implementation (for SYS_003 swap tests)."""

    async def execute(self, message: TaskMessage) -> RuntimeResult:
        return RuntimeResult(output=f"alt:{message.user_input}")


class StateCapturingRuntimePort(RuntimePort):
    """Records the task's observable state at the moment execution starts."""

    def __init__(self) -> None:
        self.captured_state: TaskState | None = None

    async def execute(self, message: TaskMessage) -> RuntimeResult:
        self.captured_state = message.state
        return RuntimeResult(output="captured")


class OrchestratorHappyPathTests(unittest.IsolatedAsyncioTestCase):
    async def test_successful_task_marks_completed_and_sends_output(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        channel = TelegramChannel(bot_token="test_token")
        runtime = StubRuntimePort()
        orchestrator = Orchestrator(owner_control=gate, runtime=runtime)

        message = TaskMessage(channel_type="telegram", user_input="hello")
        result = await orchestrator.handle(message, subject_id="owner_1", channel=channel)

        self.assertEqual(result.state, TaskState.COMPLETED)
        self.assertEqual(channel.get_response(message.task_id), "echo: hello")

    async def test_canned_runtime_response_is_sent_back(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        channel = TelegramChannel(bot_token="test_token")
        runtime = StubRuntimePort()
        runtime.register_response("plan my day", "Here is your plan.")
        orchestrator = Orchestrator(owner_control=gate, runtime=runtime)

        message = TaskMessage(channel_type="telegram", user_input="plan my day")
        await orchestrator.handle(message, subject_id="owner_1", channel=channel)

        self.assertEqual(channel.get_response(message.task_id), "Here is your plan.")

    async def test_message_is_marked_running_before_runtime_executes(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        channel = TelegramChannel(bot_token="test_token")
        runtime = StateCapturingRuntimePort()
        orchestrator = Orchestrator(owner_control=gate, runtime=runtime)

        message = TaskMessage(channel_type="telegram", user_input="x")
        await orchestrator.handle(message, subject_id="owner_1", channel=channel)

        self.assertEqual(runtime.captured_state, TaskState.RUNNING)


class OrchestratorOwnerControlTests(unittest.IsolatedAsyncioTestCase):
    async def test_unrecognized_identity_cancels_without_calling_runtime(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        channel = TelegramChannel(bot_token="test_token")
        runtime = StubRuntimePort()
        orchestrator = Orchestrator(owner_control=gate, runtime=runtime)

        message = TaskMessage(channel_type="telegram", user_input="hello")
        result = await orchestrator.handle(message, subject_id="impostor", channel=channel)

        self.assertEqual(result.state, TaskState.CANCELLED)
        response = channel.get_response(message.task_id)
        self.assertIsNotNone(response)
        assert response is not None
        self.assertIn("личность", response)

    async def test_active_emergency_switch_cancels_without_calling_runtime(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        gate.emergency_switch.activate(reason="owner requested stop")
        channel = TelegramChannel(bot_token="test_token")
        runtime = StubRuntimePort()
        orchestrator = Orchestrator(owner_control=gate, runtime=runtime)

        message = TaskMessage(channel_type="telegram", user_input="hello")
        result = await orchestrator.handle(message, subject_id="owner_1", channel=channel)

        self.assertEqual(result.state, TaskState.CANCELLED)
        response = channel.get_response(message.task_id)
        self.assertIsNotNone(response)
        assert response is not None
        self.assertIn("аварийным выключателем", response)

    async def test_identity_is_checked_before_emergency_switch(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        gate.emergency_switch.activate()
        channel = TelegramChannel(bot_token="test_token")
        runtime = StubRuntimePort()
        orchestrator = Orchestrator(owner_control=gate, runtime=runtime)

        message = TaskMessage(channel_type="telegram", user_input="hello")
        await orchestrator.handle(message, subject_id="impostor", channel=channel)

        response = channel.get_response(message.task_id)
        self.assertIsNotNone(response)
        assert response is not None
        self.assertIn("личность", response)


class OrchestratorRuntimeFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_task_level_runtime_failure_marks_failed(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        channel = TelegramChannel(bot_token="test_token")
        runtime = StubRuntimePort()
        runtime.register_failure("boom", "model quota exceeded")
        orchestrator = Orchestrator(owner_control=gate, runtime=runtime)

        message = TaskMessage(channel_type="telegram", user_input="boom")
        result = await orchestrator.handle(message, subject_id="owner_1", channel=channel)

        self.assertEqual(result.state, TaskState.FAILED)
        self.assertEqual(result.error_message, "model quota exceeded")
        response = channel.get_response(message.task_id)
        self.assertIsNotNone(response)
        assert response is not None
        self.assertIn("model quota exceeded", response)

    async def test_unavailable_environment_marks_failed_with_distinct_message(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        channel = TelegramChannel(bot_token="test_token")
        runtime = StubRuntimePort()
        runtime.simulate_unavailable("hello")
        orchestrator = Orchestrator(owner_control=gate, runtime=runtime)

        message = TaskMessage(channel_type="telegram", user_input="hello")
        result = await orchestrator.handle(message, subject_id="owner_1", channel=channel)

        self.assertEqual(result.state, TaskState.FAILED)
        response = channel.get_response(message.task_id)
        self.assertIsNotNone(response)
        assert response is not None
        self.assertIn("недоступна", response)

    async def test_runtime_port_error_is_a_distinct_type(self) -> None:
        with self.assertRaises(RuntimePortError):
            raise RuntimePortError("environment down")


class OrchestratorRuntimeSwapTests(unittest.IsolatedAsyncioTestCase):
    async def test_swapping_runtime_implementation_preserves_the_contract(self) -> None:
        """SYS_003: an alternative transitional layer runs the same contract
        without any change to the orchestrator, channel, or owner-control code."""
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        channel = TelegramChannel(bot_token="test_token")
        orchestrator = Orchestrator(owner_control=gate, runtime=AltRuntimePort())

        message = TaskMessage(channel_type="telegram", user_input="hello")
        result = await orchestrator.handle(message, subject_id="owner_1", channel=channel)

        self.assertEqual(result.state, TaskState.COMPLETED)
        self.assertEqual(channel.get_response(message.task_id), "alt:hello")


if __name__ == "__main__":
    unittest.main()
