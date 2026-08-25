"""Unit tests for the Model Gateway component (ARC_CMP_004).

Runs under the canonical `operations/scripts/quality/run_unittests.py`
discovery, so it is part of the enforced CI gate.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.channels import TaskMessage, TaskState, TelegramChannel
from src.models import (
    ModelBackedRuntimePort,
    ModelGatewayError,
    ModelRequest,
    StubModelGateway,
)
from src.orchestration import Orchestrator, RuntimePortError
from src.owner_control import OwnerControlGate


def _gate(
    owner_subject_id: str = "owner_1",
) -> tuple[OwnerControlGate, tempfile.TemporaryDirectory]:
    tmp = tempfile.TemporaryDirectory()
    gate = OwnerControlGate(owner_subject_id=owner_subject_id, state_dir=Path(tmp.name))
    return gate, tmp


class StubModelGatewayTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_response_echoes_prompt(self) -> None:
        gateway = StubModelGateway()

        response = await gateway.complete(_request("hello"))

        self.assertTrue(response.succeeded)
        self.assertEqual(response.text, "echo: hello")

    async def test_registered_response_is_returned(self) -> None:
        gateway = StubModelGateway()
        gateway.register_response("plan my day", "Here is your plan.")

        response = await gateway.complete(_request("plan my day"))

        self.assertEqual(response.text, "Here is your plan.")

    async def test_usage_metrics_are_populated_on_success(self) -> None:
        gateway = StubModelGateway()

        response = await gateway.complete(_request("one two three"))

        self.assertIsNotNone(response.usage)
        assert response.usage is not None
        self.assertEqual(response.usage.input_tokens, 3)

    async def test_registered_failure_normalizes_to_failed_response(self) -> None:
        gateway = StubModelGateway()
        gateway.register_failure("boom", "rate limit exceeded")

        response = await gateway.complete(_request("boom"))

        self.assertFalse(response.succeeded)
        self.assertEqual(response.error_message, "rate limit exceeded")

    async def test_simulated_unavailable_raises_model_gateway_error(self) -> None:
        gateway = StubModelGateway()
        gateway.simulate_unavailable("hello")

        with self.assertRaises(ModelGatewayError):
            await gateway.complete(_request("hello"))

    async def test_model_gateway_error_is_a_distinct_type(self) -> None:
        with self.assertRaises(ModelGatewayError):
            raise ModelGatewayError("provider down")


class ModelBackedRuntimePortTests(unittest.IsolatedAsyncioTestCase):
    async def test_successful_completion_becomes_runtime_output(self) -> None:
        gateway = StubModelGateway()
        gateway.register_response("hello", "hi there")
        runtime = ModelBackedRuntimePort(gateway)

        result = await runtime.execute(TaskMessage(user_input="hello"))

        self.assertTrue(result.succeeded)
        self.assertEqual(result.output, "hi there")

    async def test_failed_completion_becomes_failed_runtime_result(self) -> None:
        gateway = StubModelGateway()
        gateway.register_failure("boom", "model quota exceeded")
        runtime = ModelBackedRuntimePort(gateway)

        result = await runtime.execute(TaskMessage(user_input="boom"))

        self.assertFalse(result.succeeded)
        self.assertEqual(result.error_message, "model quota exceeded")

    async def test_gateway_outage_raises_runtime_port_error(self) -> None:
        gateway = StubModelGateway()
        gateway.simulate_unavailable("hello")
        runtime = ModelBackedRuntimePort(gateway)

        with self.assertRaises(RuntimePortError):
            await runtime.execute(TaskMessage(user_input="hello"))


class OrchestratorWithModelBackedRuntimeTests(unittest.IsolatedAsyncioTestCase):
    """End-to-end proof that ARC_CMP_004 slots into the ARC_FLOW_001 cycle
    built by TASK_003 without any change to Orchestrator, channel, or
    owner-control code (SYS_003, SYS_004)."""

    async def test_full_cycle_completes_task_via_model_gateway(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        channel = TelegramChannel(bot_token="test_token")
        gateway = StubModelGateway()
        gateway.register_response("plan my day", "Here is your plan.")
        orchestrator = Orchestrator(owner_control=gate, runtime=ModelBackedRuntimePort(gateway))

        message = TaskMessage(channel_type="telegram", user_input="plan my day")
        result = await orchestrator.handle(message, subject_id="owner_1", channel=channel)

        self.assertEqual(result.state, TaskState.COMPLETED)
        self.assertEqual(channel.get_response(message.task_id), "Here is your plan.")

    async def test_model_failure_marks_task_failed_through_full_cycle(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        channel = TelegramChannel(bot_token="test_token")
        gateway = StubModelGateway()
        gateway.register_failure("boom", "model quota exceeded")
        orchestrator = Orchestrator(owner_control=gate, runtime=ModelBackedRuntimePort(gateway))

        message = TaskMessage(channel_type="telegram", user_input="boom")
        result = await orchestrator.handle(message, subject_id="owner_1", channel=channel)

        self.assertEqual(result.state, TaskState.FAILED)
        response = channel.get_response(message.task_id)
        self.assertIsNotNone(response)
        assert response is not None
        self.assertIn("model quota exceeded", response)


def _request(prompt: str) -> ModelRequest:
    return ModelRequest(prompt=prompt)


if __name__ == "__main__":
    unittest.main()
