"""Reference ToolGateway implementation (ARC_CMP_005)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from src.observability import (
    TaskEventResult,
    TaskEventSink,
    TaskEventType,
    emit_task_event,
)
from src.owner_control.base import (
    ActionClass,
    ActionDescriptor,
    OwnerControl,
    OwnerControlError,
)

from .base import ToolCall, ToolGateway, ToolGatewayError, ToolResult

ToolHandler = Callable[[ToolCall], Awaitable[str]]


@dataclass(frozen=True)
class Capability:
    """A technically authorizable binding and its least-privilege policy."""

    name: str
    effect_class: ActionClass
    handler: ToolHandler
    allowed_subjects: frozenset[str]
    allowed_resources: frozenset[str] = field(default_factory=frozenset)
    allowed_param_names: frozenset[str] = field(default_factory=frozenset)
    allowed_secret_refs: frozenset[str] = field(default_factory=frozenset)
    allowed_network_targets: frozenset[str] = field(default_factory=frozenset)
    constraints: tuple[tuple[str, str], ...] = ()
    credential_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.allowed_subjects:
            raise ValueError("capability must name at least one allowed subject")
        if not self.allowed_resources:
            raise ValueError("capability must explicitly allow resources")


class ToolGatewayImpl(ToolGateway):
    """Single technical authorization point with fail-closed dispatch."""

    def __init__(
        self,
        owner_control: OwnerControl,
        capabilities: list[Capability],
        event_sink: TaskEventSink | None = None,
    ) -> None:
        self._owner_control = owner_control
        self._capabilities = {capability.name: capability for capability in capabilities}
        self._event_sink = event_sink

    def _emit(
        self,
        tool_call: ToolCall,
        event_type: TaskEventType,
        operation: str,
        result: TaskEventResult,
    ) -> None:
        if tool_call.runtime_task_id is None:
            return
        emit_task_event(
            self._event_sink,
            runtime_task_id=tool_call.runtime_task_id,
            event_type=event_type,
            component="tool_gateway",
            operation=operation,
            result=result,
        )

    @staticmethod
    def _denied(reason: str) -> ToolResult:
        return ToolResult(output="", succeeded=False, error_message=reason)

    async def call(self, tool_call: ToolCall) -> ToolResult:
        try:
            tool_call = tool_call.snapshot()
        except ValueError as exc:
            return self._denied(str(exc))

        try:
            self._owner_control.verify_identity(tool_call.subject_id)
            self._owner_control.check_emergency_stop()
        except OwnerControlError as exc:
            self._emit(
                tool_call,
                TaskEventType.POLICY_DECISION,
                "authorize_tool",
                TaskEventResult.DENIED,
            )
            return self._denied(str(exc))

        capability = self._capabilities.get(tool_call.capability_name)
        if capability is None:
            self._emit(
                tool_call,
                TaskEventType.POLICY_DECISION,
                "authorize_tool",
                TaskEventResult.DENIED,
            )
            return self._denied(f"unknown capability: {tool_call.capability_name}")
        if tool_call.subject_id not in capability.allowed_subjects:
            self._emit(
                tool_call,
                TaskEventType.POLICY_DECISION,
                "authorize_tool",
                TaskEventResult.DENIED,
            )
            return self._denied("subject not authorized for capability")
        if tool_call.resource not in capability.allowed_resources:
            self._emit(
                tool_call,
                TaskEventType.POLICY_DECISION,
                "authorize_tool",
                TaskEventResult.DENIED,
            )
            return self._denied(f"resource not authorized for capability: {tool_call.resource}")
        if not set(tool_call.params).issubset(capability.allowed_param_names):
            self._emit(
                tool_call,
                TaskEventType.POLICY_DECISION,
                "authorize_tool",
                TaskEventResult.DENIED,
            )
            return self._denied("parameters not authorized for capability")
        if not tool_call.secret_refs.issubset(capability.allowed_secret_refs):
            self._emit(
                tool_call,
                TaskEventType.POLICY_DECISION,
                "authorize_tool",
                TaskEventResult.DENIED,
            )
            return self._denied("secret reference not authorized for capability")
        if tool_call.network_target is not None and (
            tool_call.network_target not in capability.allowed_network_targets
        ):
            self._emit(
                tool_call,
                TaskEventType.POLICY_DECISION,
                "authorize_tool",
                TaskEventResult.DENIED,
            )
            return self._denied("network target not authorized for capability")

        try:
            action = ActionDescriptor.create(
                subject_id=tool_call.subject_id,
                capability_name=capability.name,
                resource=tool_call.resource,
                action_class=capability.effect_class,
                params=tool_call.params,
                secret_refs=tuple(tool_call.secret_refs),
                network_target=tool_call.network_target,
                constraints=capability.constraints,
                credential_ref=capability.credential_ref,
            )
            decision = self._owner_control.authorize_sensitive_action(
                tool_call.action_id,
                action,
                confirmed=tool_call.confirmed,
            )
            if not decision.authorized:
                self._emit(
                    tool_call,
                    TaskEventType.POLICY_DECISION,
                    "authorize_tool",
                    TaskEventResult.DENIED,
                )
                return self._denied(decision.reason)
            self._owner_control.check_emergency_stop()
        except (OwnerControlError, ValueError) as exc:
            self._emit(
                tool_call,
                TaskEventType.POLICY_DECISION,
                "authorize_tool",
                TaskEventResult.DENIED,
            )
            return self._denied(str(exc))

        self._emit(
            tool_call,
            TaskEventType.POLICY_DECISION,
            "authorize_tool",
            TaskEventResult.ALLOWED,
        )

        try:
            output = await capability.handler(tool_call)
        except Exception as exc:
            self._emit(
                tool_call,
                TaskEventType.TOOL_CALL,
                "dispatch",
                TaskEventResult.FAILED,
            )
            self._emit(
                tool_call,
                TaskEventType.ERROR,
                "tool_unavailable",
                TaskEventResult.FAILED,
            )
            raise ToolGatewayError("tool call failed") from exc
        self._emit(
            tool_call,
            TaskEventType.TOOL_CALL,
            "dispatch",
            TaskEventResult.SUCCEEDED,
        )
        return ToolResult(output=output)
