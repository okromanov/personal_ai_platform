"""Reference ToolGateway implementation (ARC_CMP_005).

Every call is authorized before it reaches a handler: an unknown
capability or an unlisted resource is rejected outright, and the impact
class registered on the capability -- never anything supplied in the
call's own params -- is what OwnerControl checks (SEC_CTL_007). Sensitive
classes route through `OwnerControl.authorize_sensitive_action`
(ARC_CMP_002) for the owner's confirmation, with duplicate protection
built into that same call (SEC_CTL_008).
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from src.owner_control.base import ActionClass, OwnerControl

from .base import ToolCall, ToolGateway, ToolGatewayError, ToolResult

ToolHandler = Callable[[ToolCall], Awaitable[str]]


@dataclass(frozen=True)
class Capability:
    """A registered, technically authorizable tool binding (SEC_CTL_007).

    Attributes:
        name: Unique capability identifier a ToolCall requests by name.
        effect_class: Impact classification (SEC_CTL_008) -- fixed at
            registration time, not something a caller can influence.
        handler: Executes an authorized call and returns its output.
        allowed_resources: Resources this capability may act on. Empty
            means unrestricted -- appropriate only for `ActionClass.READ`.
    """

    name: str
    effect_class: ActionClass
    handler: ToolHandler
    allowed_resources: frozenset[str] = field(default_factory=frozenset)


class ToolGatewayImpl(ToolGateway):
    """Reference `ToolGateway`: technical authorization plus dispatch."""

    def __init__(self, owner_control: OwnerControl, capabilities: list[Capability]) -> None:
        self._owner_control = owner_control
        self._capabilities = {capability.name: capability for capability in capabilities}

    async def call(self, tool_call: ToolCall) -> ToolResult:
        capability = self._capabilities.get(tool_call.capability_name)
        if capability is None:
            return ToolResult(
                output="",
                succeeded=False,
                error_message=f"unknown capability: {tool_call.capability_name}",
            )
        if capability.allowed_resources and tool_call.resource not in capability.allowed_resources:
            return ToolResult(
                output="",
                succeeded=False,
                error_message=f"resource not authorized for capability: {tool_call.resource}",
            )

        decision = self._owner_control.authorize_sensitive_action(
            tool_call.action_id,
            capability.effect_class,
            tool_call.params,
            confirmed=tool_call.confirmed,
        )
        if not decision.authorized:
            return ToolResult(output="", succeeded=False, error_message=decision.reason)

        try:
            output = await capability.handler(tool_call)
        except Exception as exc:
            raise ToolGatewayError(f"tool call failed: {exc}") from exc
        return ToolResult(output=output)
