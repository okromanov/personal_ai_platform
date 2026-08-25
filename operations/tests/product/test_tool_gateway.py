"""Unit tests for the Tool Gateway component (ARC_CMP_005).

Runs under the canonical `operations/scripts/quality/run_unittests.py`
discovery, so it is part of the enforced CI gate.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.owner_control import ActionClass, OwnerControlGate
from src.tools import Capability, ToolCall, ToolGatewayError, ToolGatewayImpl


def _gate(
    owner_subject_id: str = "owner_1",
) -> tuple[OwnerControlGate, tempfile.TemporaryDirectory]:
    tmp = tempfile.TemporaryDirectory()
    gate = OwnerControlGate(owner_subject_id=owner_subject_id, state_dir=Path(tmp.name))
    return gate, tmp


async def _read_file(call: ToolCall) -> str:
    return f"contents of {call.resource}"


class RecordingHandler:
    """A handler that records whether it was ever invoked (testing only)."""

    def __init__(self, output: str = "done") -> None:
        self.calls: list[ToolCall] = []
        self._output = output

    async def __call__(self, call: ToolCall) -> str:
        self.calls.append(call)
        return self._output


async def _boom(call: ToolCall) -> str:
    raise RuntimeError("underlying tool crashed")


class ToolGatewayReadTests(unittest.IsolatedAsyncioTestCase):
    async def test_read_capability_authorized_immediately_without_confirmation(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        capability = Capability(name="read_file", effect_class=ActionClass.READ, handler=_read_file)
        gateway = ToolGatewayImpl(owner_control=gate, capabilities=[capability])

        result = await gateway.call(
            ToolCall(action_id="a1", capability_name="read_file", resource="notes.txt")
        )

        self.assertTrue(result.succeeded)
        self.assertEqual(result.output, "contents of notes.txt")


class ToolGatewaySensitiveActionTests(unittest.IsolatedAsyncioTestCase):
    async def test_sensitive_capability_requires_confirmation_first(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        handler = RecordingHandler()
        capability = Capability(
            name="send_email", effect_class=ActionClass.WRITE_EXTERNAL, handler=handler
        )
        gateway = ToolGatewayImpl(owner_control=gate, capabilities=[capability])

        result = await gateway.call(
            ToolCall(
                action_id="send-1",
                capability_name="send_email",
                resource="owner@example.com",
                params={"subject": "hi"},
            )
        )

        self.assertFalse(result.succeeded)
        self.assertEqual(handler.calls, [])

    async def test_sensitive_capability_authorized_on_matching_confirmation(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        handler = RecordingHandler(output="sent")
        capability = Capability(
            name="send_email", effect_class=ActionClass.WRITE_EXTERNAL, handler=handler
        )
        gateway = ToolGatewayImpl(owner_control=gate, capabilities=[capability])
        call = ToolCall(
            action_id="send-1",
            capability_name="send_email",
            resource="owner@example.com",
            params={"subject": "hi"},
        )
        await gateway.call(call)

        result = await gateway.call(
            ToolCall(
                action_id="send-1",
                capability_name="send_email",
                resource="owner@example.com",
                params={"subject": "hi"},
                confirmed=True,
            )
        )

        self.assertTrue(result.succeeded)
        self.assertEqual(result.output, "sent")
        self.assertEqual(len(handler.calls), 1)

    async def test_duplicate_action_id_rejected_after_authorization(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        handler = RecordingHandler()
        capability = Capability(
            name="send_email", effect_class=ActionClass.WRITE_EXTERNAL, handler=handler
        )
        gateway = ToolGatewayImpl(owner_control=gate, capabilities=[capability])
        params = {"subject": "hi"}
        await gateway.call(
            ToolCall(
                action_id="send-1",
                capability_name="send_email",
                resource="owner@example.com",
                params=params,
            )
        )
        await gateway.call(
            ToolCall(
                action_id="send-1",
                capability_name="send_email",
                resource="owner@example.com",
                params=params,
                confirmed=True,
            )
        )

        result = await gateway.call(
            ToolCall(
                action_id="send-1",
                capability_name="send_email",
                resource="owner@example.com",
                params=params,
                confirmed=True,
            )
        )

        self.assertFalse(result.succeeded)
        self.assertEqual(len(handler.calls), 1)


class ToolGatewayDenialTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_capability_returns_failed_result(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        gateway = ToolGatewayImpl(owner_control=gate, capabilities=[])

        result = await gateway.call(
            ToolCall(action_id="a1", capability_name="does_not_exist", resource="x")
        )

        self.assertFalse(result.succeeded)
        assert result.error_message is not None
        self.assertIn("unknown capability", result.error_message)

    async def test_resource_outside_allowlist_is_denied(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        handler = RecordingHandler()
        capability = Capability(
            name="read_file",
            effect_class=ActionClass.READ,
            handler=handler,
            allowed_resources=frozenset({"allowed.txt"}),
        )
        gateway = ToolGatewayImpl(owner_control=gate, capabilities=[capability])

        result = await gateway.call(
            ToolCall(action_id="a1", capability_name="read_file", resource="secret.txt")
        )

        self.assertFalse(result.succeeded)
        self.assertEqual(handler.calls, [])

    async def test_capability_effect_class_cannot_be_overridden_by_call_params(self) -> None:
        """SEC_CTL_007: the fixed, registered effect_class governs
        authorization -- a caller cannot claim a weaker class through the
        call's own params to skip the owner-confirmation step."""
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        handler = RecordingHandler()
        capability = Capability(
            name="delete_file", effect_class=ActionClass.DESTRUCTIVE, handler=handler
        )
        gateway = ToolGatewayImpl(owner_control=gate, capabilities=[capability])

        result = await gateway.call(
            ToolCall(
                action_id="del-1",
                capability_name="delete_file",
                resource="report.txt",
                params={"effect_class": "read"},
            )
        )

        self.assertFalse(result.succeeded)
        self.assertEqual(handler.calls, [])


class ToolGatewayFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_handler_exception_raises_tool_gateway_error(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        capability = Capability(name="crash", effect_class=ActionClass.READ, handler=_boom)
        gateway = ToolGatewayImpl(owner_control=gate, capabilities=[capability])

        with self.assertRaises(ToolGatewayError):
            await gateway.call(ToolCall(action_id="a1", capability_name="crash", resource="x"))

    async def test_tool_gateway_error_is_a_distinct_type(self) -> None:
        with self.assertRaises(ToolGatewayError):
            raise ToolGatewayError("tool unavailable")


if __name__ == "__main__":
    unittest.main()
