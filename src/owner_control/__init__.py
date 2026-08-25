"""Owner control layer: identity, emergency switch and sensitive-action gate.

Verifies identity, owner rules, emergency state and applicable conditions
before a task starts or continues, and again before a sensitive external
action. Owns no task orchestration, memory, or tool execution.

This module implements ARC_CMP_002 — Контроль владельца (Owner Control).
"""

from .base import (
    ActionClass,
    AuthorizationDecision,
    EmergencyStopActive,
    IdentityRejected,
    OwnerControl,
    OwnerControlError,
)
from .control import OwnerControlGate
from .emergency_switch import EmergencySwitch

__all__ = [
    "ActionClass",
    "AuthorizationDecision",
    "EmergencyStopActive",
    "EmergencySwitch",
    "IdentityRejected",
    "OwnerControl",
    "OwnerControlError",
    "OwnerControlGate",
]
