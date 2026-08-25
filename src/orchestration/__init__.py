"""Task orchestration and the RuntimePort boundary.

Turns a normalized task into an executable cycle and connects a swappable
agent execution environment through a stable RuntimePort. Owns no owner
secrets, owner-control state, or canonical long-lived memory.

This module implements ARC_CMP_003 — Оркестрация и RuntimePort.
"""

from .orchestrator import Orchestrator
from .runtime_port import RuntimePort, RuntimePortError, RuntimeResult
from .stub_runtime import StubRuntimePort

__all__ = [
    "Orchestrator",
    "RuntimePort",
    "RuntimePortError",
    "RuntimeResult",
    "StubRuntimePort",
]
