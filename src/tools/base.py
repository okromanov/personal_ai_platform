"""Tool gateway abstraction (ARC_CMP_005).

Single point of technical authorization for every tool call. A capability
declares the allowed subject, resource, effect class, data, secrets,
network, and constraints (SEC_CTL_007); MCP or any other integration
protocol is only a way to connect a tool, never a source of authorization
-- discovered metadata about a tool remains untrusted data and never
creates a permission or weakens the effect-class check on its own.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ToolGatewayError(Exception):
    """Raised when the underlying tool itself cannot even be reached (crashed, unavailable)."""


@dataclass(frozen=True)
class ToolCall:
    """A single requested invocation of a registered capability.

    Attributes:
        action_id: Caller-supplied identifier used for duplicate protection
            (SEC_CTL_008) and to correlate an owner confirmation with this
            exact call.
        capability_name: The capability being invoked.
        resource: The concrete resource this call acts on.
        params: Concrete significant parameters of the call.
        confirmed: Whether the owner has confirmed these exact parameters;
            required before a sensitive call is authorized.
    """

    action_id: str
    capability_name: str
    resource: str
    params: dict[str, Any] = field(default_factory=dict)
    confirmed: bool = False


@dataclass(frozen=True)
class ToolResult:
    """Normalized outcome of one tool call.

    Attributes:
        output: Result produced by the tool.
        succeeded: Whether the call completed without error.
        error_message: Present when succeeded is False -- covers both a
            denied authorization and a controlled tool-side failure.
    """

    output: str
    succeeded: bool = True
    error_message: str | None = None


class ToolGateway(ABC):
    """Abstract contract for the single technical-authorization point for tools.

    Implementations own the concrete registry of capabilities and how a
    call is dispatched to its underlying tool (a local function, an MCP
    server, an HTTP API, ...). Swapping the implementation must not
    require changes to the orchestrator or owner-control code above this
    boundary.
    """

    @abstractmethod
    async def call(self, tool_call: ToolCall) -> ToolResult:
        """Authorize and execute one tool call.

        Args:
            tool_call: The requested invocation.

        Returns:
            ToolResult with the produced output, or a controlled failure
            (`succeeded=False`) for an expected per-call outcome such as a
            denied authorization, an unknown capability, or a tool-side
            failure reported by the handler.

        Raises:
            ToolGatewayError: If the underlying tool itself cannot even be
                reached (crashed, unavailable). Expected per-call failures
                should be returned as a failed ToolResult instead.
        """
