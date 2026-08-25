"""Tool gateway: the single technical-authorization point for tool calls.

Provides a stable contract (ToolGateway) for authorizing and executing a
tool call, independent of how the tool is reached (a local function, an
MCP server, an HTTP API, ...). Registered capabilities carry a fixed
impact class (SEC_CTL_008) checked through OwnerControl before dispatch,
so a caller cannot escalate its own authorization by claiming a different
class or by relying on tool-discovery metadata (SEC_CTL_007).

This module implements ARC_CMP_005 — Шлюз инструментов (Tool Gateway).
"""

from .base import ToolCall, ToolGateway, ToolGatewayError, ToolResult
from .registry import Capability, ToolGatewayImpl, ToolHandler

__all__ = [
    "Capability",
    "ToolCall",
    "ToolGateway",
    "ToolGatewayError",
    "ToolGatewayImpl",
    "ToolHandler",
    "ToolResult",
]
