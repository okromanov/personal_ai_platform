"""Unit tests for the Tool Gateway component (ARC_CMP_005)."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from src.owner_control import ActionClass, OwnerControlGate
from src.tools import Capability, ToolCall, ToolGatewayError, ToolGatewayImpl


def _gate() -> tuple[OwnerControlGate, tempfile.TemporaryDirectory]:
    tmp = tempfile.TemporaryDirectory()
    gate = OwnerControlGate(owner_subject_id="owner_1", state_dir=Path(tmp.name))
    return gate, tmp


def _call(
    *,
    action_id: str = "a1",
    capability_name: str = "read_file",
    resource: str = "notes.txt",
    subject_id: str = "owner_1",
    params: dict[str, object] | None = None,
    confirmed: bool = False,
    secret_refs: frozenset[str] = frozenset(),
    network_target: str | None = None,
) -> ToolCall:
    return ToolCall(
        action_id=action_id,
        subject_id=subject_id,
        capability_name=capability_name,
        resource=resource,
        params=params or {},
        confirmed=confirmed,
        secret_refs=secret_refs,
        network_target=network_target,
    )


class RecordingHandler:
    def __init__(self, output: str = "done") -> None:
        self.calls: list[ToolCall] = []
        self._output = output

    async def __call__(self, call: ToolCall) -> str:
        self.calls.append(call)
        return self._output


async def _boom(call: ToolCall) -> str:
    raise RuntimeError(f"underlying tool crashed for {call.resource}")


def _capability(
    *,
    name: str = "read_file",
    effect_class: ActionClass = ActionClass.READ,
    handler: RecordingHandler | object,
    resources: frozenset[str] = frozenset(),
    params: frozenset[str] = frozenset(),
    subjects: frozenset[str] = frozenset({"owner_1"}),
    secret_refs: frozenset[str] = frozenset(),
    network_targets: frozenset[str] = frozenset(),
) -> Capability:
    return Capability(
        name=name,
        effect_class=effect_class,
        handler=handler,  # type: ignore[arg-type]
        allowed_subjects=subjects,
        allowed_resources=resources,
        allowed_param_names=params,
        allowed_secret_refs=secret_refs,
        allowed_network_targets=network_targets,
    )


class CapabilityPolicyTests(unittest.TestCase):
    def test_capability_requires_an_allowed_subject(self) -> None:
        with self.assertRaises(ValueError):
            _capability(handler=RecordingHandler(), subjects=frozenset())

    @unittest.expectedFailure
    def test_read_capability_requires_explicit_resources(self) -> None:
        with self.assertRaises(ValueError):
            _capability(handler=RecordingHandler(), resources=frozenset())

    def test_sensitive_capability_requires_explicit_resources(self) -> None:
        with self.assertRaises(ValueError):
            _capability(
                name="send_email",
                effect_class=ActionClass.WRITE_EXTERNAL,
                handler=RecordingHandler(),
            )


class ToolGatewayReadTests(unittest.IsolatedAsyncioTestCase):
    async def test_read_capability_authorized_immediately(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        handler = RecordingHandler("contents")
        gateway = ToolGatewayImpl(gate, [_capability(handler=handler)])
        result = await gateway.call(_call())
        self.assertTrue(result.succeeded)
        self.assertEqual(result.output, "contents")
        self.assertEqual(len(handler.calls), 1)

    async def test_unrecognized_subject_is_denied_before_handler(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        handler = RecordingHandler()
        gateway = ToolGatewayImpl(gate, [_capability(handler=handler)])
        result = await gateway.call(_call(subject_id="impostor"))
        self.assertFalse(result.succeeded)
        self.assertEqual(handler.calls, [])

    async def test_non_json_params_are_denied_before_handler(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        handler = RecordingHandler()
        gateway = ToolGatewayImpl(
            gate,
            [_capability(handler=handler, params=frozenset({"value"}))],
        )

        result = await gateway.call(_call(params={"value": object()}))

        self.assertFalse(result.succeeded)
        self.assertEqual(result.error_message, "tool call params must be JSON-serializable")
        self.assertEqual(handler.calls, [])


class ToolGatewaySensitiveActionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.gate, self.tmp = _gate()
        self.addCleanup(self.tmp.cleanup)
        self.handler = RecordingHandler("sent")
        self.capability = _capability(
            name="send_email",
            effect_class=ActionClass.WRITE_EXTERNAL,
            handler=self.handler,
            resources=frozenset({"a@example.com", "b@example.com"}),
            params=frozenset({"subject"}),
        )
        self.gateway = ToolGatewayImpl(self.gate, [self.capability])

    async def test_sensitive_capability_requires_confirmation_first(self) -> None:
        result = await self.gateway.call(
            _call(
                action_id="send-1",
                capability_name="send_email",
                resource="a@example.com",
                params={"subject": "hi"},
            )
        )
        self.assertFalse(result.succeeded)
        self.assertEqual(handler_calls := self.handler.calls, [])
        self.assertEqual(len(handler_calls), 0)

    async def test_matching_confirmation_executes_once(self) -> None:
        first = _call(
            action_id="send-2",
            capability_name="send_email",
            resource="a@example.com",
            params={"subject": "hi"},
        )
        await self.gateway.call(first)
        result = await self.gateway.call(
            _call(
                action_id="send-2",
                capability_name="send_email",
                resource="a@example.com",
                params={"subject": "hi"},
                confirmed=True,
            )
        )
        self.assertTrue(result.succeeded)
        self.assertEqual(result.output, "sent")
        self.assertEqual(len(self.handler.calls), 1)

    async def test_dispatch_uses_the_exact_deep_snapshot_that_was_authorized(self) -> None:
        started = asyncio.Event()
        resume = asyncio.Event()
        observed: list[object] = []

        async def delayed_handler(call: ToolCall) -> str:
            started.set()
            await resume.wait()
            observed.append(call.params["subject"])
            return "sent"

        gateway = ToolGatewayImpl(
            self.gate,
            [
                _capability(
                    name="send_email",
                    effect_class=ActionClass.WRITE_EXTERNAL,
                    handler=delayed_handler,
                    resources=frozenset({"a@example.com"}),
                    params=frozenset({"subject"}),
                )
            ],
        )
        subject = {"label": "APPROVED"}
        params: dict[str, object] = {"subject": subject}
        first = _call(
            action_id="send-snapshot",
            capability_name="send_email",
            resource="a@example.com",
            params=params,
        )
        self.assertFalse((await gateway.call(first)).succeeded)

        confirmed = _call(
            action_id="send-snapshot",
            capability_name="send_email",
            resource="a@example.com",
            params=params,
            confirmed=True,
        )
        execution = asyncio.create_task(gateway.call(confirmed))
        await asyncio.wait_for(started.wait(), timeout=2)
        subject["label"] = "NOT_APPROVED"
        resume.set()
        result = await asyncio.wait_for(execution, timeout=2)

        self.assertTrue(result.succeeded)
        self.assertEqual(observed, [{"label": "APPROVED"}])

    async def test_confirmation_cannot_be_reused_for_another_resource(self) -> None:
        await self.gateway.call(
            _call(action_id="send-3", capability_name="send_email", resource="a@example.com")
        )
        result = await self.gateway.call(
            _call(
                action_id="send-3",
                capability_name="send_email",
                resource="b@example.com",
                confirmed=True,
            )
        )
        self.assertFalse(result.succeeded)
        self.assertEqual(self.handler.calls, [])

    async def test_confirmation_cannot_be_reused_for_another_capability(self) -> None:
        second = _capability(
            name="archive_email",
            effect_class=ActionClass.WRITE_EXTERNAL,
            handler=self.handler,
            resources=frozenset({"a@example.com"}),
        )
        gateway = ToolGatewayImpl(self.gate, [self.capability, second])
        await gateway.call(
            _call(action_id="send-4", capability_name="send_email", resource="a@example.com")
        )
        result = await gateway.call(
            _call(
                action_id="send-4",
                capability_name="archive_email",
                resource="a@example.com",
                confirmed=True,
            )
        )
        self.assertFalse(result.succeeded)
        self.assertEqual(self.handler.calls, [])

    async def test_switch_activated_before_confirmation_blocks_dispatch(self) -> None:
        call = _call(action_id="send-5", capability_name="send_email", resource="a@example.com")
        await self.gateway.call(call)
        self.gate.emergency_switch.activate()
        result = await self.gateway.call(
            _call(
                action_id="send-5",
                capability_name="send_email",
                resource="a@example.com",
                confirmed=True,
            )
        )
        self.assertFalse(result.succeeded)
        self.assertEqual(self.handler.calls, [])

    async def test_switch_activated_after_authorization_blocks_dispatch(self) -> None:
        gate = self.gate
        original = gate.authorize_sensitive_action

        def authorize_then_stop(*args: object, **kwargs: object):
            decision = original(*args, **kwargs)  # type: ignore[arg-type]
            if decision.authorized:
                gate.emergency_switch.activate()
            return decision

        gate.authorize_sensitive_action = authorize_then_stop  # type: ignore[method-assign]
        call = _call(action_id="send-6", capability_name="send_email", resource="a@example.com")
        await self.gateway.call(call)
        result = await self.gateway.call(
            _call(
                action_id="send-6",
                capability_name="send_email",
                resource="a@example.com",
                confirmed=True,
            )
        )
        self.assertFalse(result.succeeded)
        self.assertEqual(self.handler.calls, [])

    async def test_duplicate_action_remains_blocked_after_restart(self) -> None:
        call = _call(action_id="send-7", capability_name="send_email", resource="a@example.com")
        await self.gateway.call(call)
        await self.gateway.call(
            _call(
                action_id="send-7",
                capability_name="send_email",
                resource="a@example.com",
                confirmed=True,
            )
        )
        restarted = OwnerControlGate("owner_1", Path(self.tmp.name))
        gateway = ToolGatewayImpl(restarted, [self.capability])
        replay = await gateway.call(
            _call(
                action_id="send-7",
                capability_name="send_email",
                resource="a@example.com",
                confirmed=True,
            )
        )
        self.assertFalse(replay.succeeded)
        self.assertEqual(len(self.handler.calls), 1)


class ToolGatewayPolicyDenialTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_capability_returns_failed_result(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        result = await ToolGatewayImpl(gate, []).call(_call(capability_name="missing"))
        self.assertFalse(result.succeeded)
        self.assertIn("unknown capability", result.error_message or "")

    async def test_resource_outside_allowlist_is_denied(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        handler = RecordingHandler()
        capability = _capability(handler=handler, resources=frozenset({"allowed.txt"}))
        result = await ToolGatewayImpl(gate, [capability]).call(_call(resource="secret.txt"))
        self.assertFalse(result.succeeded)
        self.assertEqual(handler.calls, [])

    async def test_unlisted_parameter_is_denied(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        handler = RecordingHandler()
        gateway = ToolGatewayImpl(gate, [_capability(handler=handler)])
        result = await gateway.call(_call(params={"unexpected": True}))
        self.assertFalse(result.succeeded)
        self.assertEqual(handler.calls, [])

    async def test_secret_and_network_target_must_be_explicitly_allowed(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        handler = RecordingHandler()
        capability = _capability(handler=handler)
        gateway = ToolGatewayImpl(gate, [capability])
        secret_result = await gateway.call(_call(secret_refs=frozenset({"mail-token"})))
        network_result = await gateway.call(_call(action_id="a2", network_target="api.test"))
        self.assertFalse(secret_result.succeeded)
        self.assertFalse(network_result.succeeded)
        self.assertEqual(handler.calls, [])

    async def test_corrupt_switch_state_denies_without_handler(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        handler = RecordingHandler()
        gate.emergency_switch._path.write_text("partial", encoding="utf-8")
        result = await ToolGatewayImpl(gate, [_capability(handler=handler)]).call(_call())
        self.assertFalse(result.succeeded)
        self.assertEqual(handler.calls, [])


class ToolGatewayFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_handler_exception_raises_tool_gateway_error(self) -> None:
        gate, tmp = _gate()
        self.addCleanup(tmp.cleanup)
        capability = _capability(handler=_boom)
        gateway = ToolGatewayImpl(gate, [capability])
        with self.assertRaises(ToolGatewayError):
            await gateway.call(_call())


if __name__ == "__main__":
    unittest.main()
