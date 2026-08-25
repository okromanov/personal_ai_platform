"""Owner control gate implementation (ARC_CMP_002).

Minimal working implementation for m02: the owner identity and emergency
switch use a local file instead of an external secret store. Real admin
identity protection (multi-factor authentication on GitHub/hosting) is an
operational practice outside this component's code scope -- see TEST_008
section 6.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .base import (
    SENSITIVE_ACTION_CLASSES,
    ActionClass,
    AuthorizationDecision,
    EmergencyStopActive,
    IdentityRejected,
    OwnerControl,
)
from .emergency_switch import EmergencySwitch


@dataclass
class _PendingAction:
    """A sensitive action awaiting owner confirmation of its exact parameters."""

    action_class: ActionClass
    params: dict[str, Any] = field(default_factory=dict)


class OwnerControlGate(OwnerControl):
    """Reference `OwnerControl` implementation for a single owner identity."""

    def __init__(self, owner_subject_id: str, state_dir: Path) -> None:
        """Initialize the gate.

        Args:
            owner_subject_id: The one recognized owner identity (e.g. Telegram user id).
            state_dir: Directory used to persist the emergency switch state.

        Raises:
            ValueError: If owner_subject_id is empty.
        """
        if not owner_subject_id:
            raise ValueError("owner_subject_id must not be empty")
        self._owner_subject_id = owner_subject_id
        self.emergency_switch = EmergencySwitch(state_dir / "emergency_switch.json")
        self._pending_actions: dict[str, _PendingAction] = {}
        self._authorized_action_ids: set[str] = set()

    def verify_identity(self, subject_id: str) -> None:
        if subject_id != self._owner_subject_id:
            raise IdentityRejected(f"subject '{subject_id}' is not the recognized owner")

    def check_emergency_stop(self) -> None:
        if self.emergency_switch.is_active():
            raise EmergencyStopActive("emergency switch is active")

    def authorize_sensitive_action(
        self,
        action_id: str,
        action_class: ActionClass,
        params: dict[str, Any],
        *,
        confirmed: bool = False,
    ) -> AuthorizationDecision:
        if action_id in self._authorized_action_ids:
            return AuthorizationDecision(
                authorized=False,
                action_id=action_id,
                reason="duplicate action_id already authorized",
            )

        if action_class not in SENSITIVE_ACTION_CLASSES:
            self._authorized_action_ids.add(action_id)
            return AuthorizationDecision(
                authorized=True, action_id=action_id, reason="not sensitive"
            )

        if not confirmed:
            self._pending_actions[action_id] = _PendingAction(action_class, dict(params))
            return AuthorizationDecision(
                authorized=False,
                action_id=action_id,
                reason="owner confirmation required",
            )

        pending = self._pending_actions.get(action_id)
        if pending is None or pending.action_class != action_class or pending.params != params:
            return AuthorizationDecision(
                authorized=False,
                action_id=action_id,
                reason="confirmation does not match the requested action",
            )

        del self._pending_actions[action_id]
        self._authorized_action_ids.add(action_id)
        return AuthorizationDecision(authorized=True, action_id=action_id, reason="owner confirmed")
