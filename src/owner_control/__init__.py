"""Owner control layer: identity, emergency switch and sensitive-action gate.

Verifies identity, owner rules, emergency state and applicable conditions
before a task starts or continues, and again before a sensitive external
action. Owns no task orchestration, memory, or tool execution.

This module implements ARC_CMP_002 — Контроль владельца (Owner Control).
"""

from .base import (
    ActionClass,
    ActionDescriptor,
    AuthorizationDecision,
    EmergencyStopActive,
    EmergencySwitchStateError,
    IdentityRejected,
    OwnerControl,
    OwnerControlError,
    OwnerControlStateError,
)
from .control import (
    RECOVERY_CONFIRMATION_PHRASE,
    OwnerControlGate,
    StaleLockRecoveryError,
    recover_stale_sensitive_action_lock,
)
from .emergency_switch import EmergencySwitch

__all__ = [
    "RECOVERY_CONFIRMATION_PHRASE",
    "ActionDescriptor",
    "ActionClass",
    "AuthorizationDecision",
    "EmergencyStopActive",
    "EmergencySwitch",
    "EmergencySwitchStateError",
    "IdentityRejected",
    "OwnerControl",
    "OwnerControlError",
    "OwnerControlGate",
    "OwnerControlStateError",
    "StaleLockRecoveryError",
    "recover_stale_sensitive_action_lock",
]
