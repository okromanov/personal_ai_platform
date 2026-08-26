"""Owner control gate implementation (ARC_CMP_002)."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .base import (
    SENSITIVE_ACTION_CLASSES,
    ActionClass,
    ActionDescriptor,
    AuthorizationDecision,
    EmergencyStopActive,
    EmergencySwitchStateError,
    IdentityRejected,
    OwnerControl,
    OwnerControlStateError,
)
from .emergency_switch import EmergencySwitch
from .state_io import atomic_write_json, read_json_object


def _serialize_action(action: ActionDescriptor) -> dict[str, Any]:
    return {
        "subject_id": action.subject_id,
        "capability_name": action.capability_name,
        "resource": action.resource,
        "action_class": action.action_class.value,
        "params_json": action.params_json,
        "secret_refs": list(action.secret_refs),
        "network_target": action.network_target,
        "constraints": [list(item) for item in action.constraints],
        "credential_ref": action.credential_ref,
    }


def _deserialize_action(raw: object) -> ActionDescriptor:
    if not isinstance(raw, dict):
        raise OwnerControlStateError("pending action state must be an object")
    try:
        return ActionDescriptor(
            subject_id=str(raw["subject_id"]),
            capability_name=str(raw["capability_name"]),
            resource=str(raw["resource"]),
            action_class=ActionClass(str(raw["action_class"])),
            params_json=str(raw["params_json"]),
            secret_refs=tuple(str(item) for item in raw.get("secret_refs", [])),
            network_target=(
                str(raw["network_target"]) if raw.get("network_target") is not None else None
            ),
            constraints=tuple((str(item[0]), str(item[1])) for item in raw.get("constraints", [])),
            credential_ref=(
                str(raw["credential_ref"]) if raw.get("credential_ref") is not None else None
            ),
        )
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise OwnerControlStateError("pending action state is malformed") from exc


class OwnerControlGate(OwnerControl):
    """Single-owner gate with durable confirmation and duplicate state."""

    def __init__(self, owner_subject_id: str, state_dir: Path) -> None:
        if not owner_subject_id:
            raise ValueError("owner_subject_id must not be empty")
        self._owner_subject_id = owner_subject_id
        self._state_dir = state_dir
        self.emergency_switch = EmergencySwitch(state_dir / "emergency_switch.json")
        self._actions_path = state_dir / "owner_control_actions.json"
        self._actions_lock_path = state_dir / "owner_control_actions.lock"

    def verify_identity(self, subject_id: str) -> None:
        if subject_id != self._owner_subject_id:
            raise IdentityRejected(f"subject '{subject_id}' is not the recognized owner")

    def check_emergency_stop(self) -> None:
        try:
            active = self.emergency_switch.is_active()
        except EmergencySwitchStateError as exc:
            raise EmergencyStopActive("emergency switch state cannot be trusted") from exc
        if active:
            raise EmergencyStopActive("emergency switch is active")

    @contextmanager
    def _exclusive_state(self) -> Iterator[None]:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.mkdir(self._actions_lock_path)
        except FileExistsError as exc:
            raise OwnerControlStateError(
                "owner-control state is locked or recovery is required"
            ) from exc
        try:
            yield
        finally:
            try:
                os.rmdir(self._actions_lock_path)
            except OSError as exc:
                raise OwnerControlStateError(
                    "owner-control state lock could not be released"
                ) from exc

    def _load_actions(self) -> tuple[dict[str, ActionDescriptor], set[str]]:
        if not self._actions_path.is_file():
            return {}, set()
        try:
            raw = read_json_object(self._actions_path)
            pending_raw = raw.get("pending", {})
            authorized_raw = raw.get("authorized_action_ids", [])
            if not isinstance(pending_raw, dict) or not isinstance(authorized_raw, list):
                raise ValueError("invalid action state shape")
            pending = {
                str(action_id): _deserialize_action(descriptor)
                for action_id, descriptor in pending_raw.items()
            }
            authorized = {str(action_id) for action_id in authorized_raw}
            return pending, authorized
        except (ValueError, TypeError) as exc:
            if isinstance(exc, OwnerControlStateError):
                raise
            raise OwnerControlStateError("owner-control action state cannot be trusted") from exc

    def _save_actions(self, pending: dict[str, ActionDescriptor], authorized: set[str]) -> None:
        atomic_write_json(
            self._actions_path,
            {
                "pending": {
                    action_id: _serialize_action(descriptor)
                    for action_id, descriptor in sorted(pending.items())
                },
                "authorized_action_ids": sorted(authorized),
            },
        )

    def authorize_sensitive_action(
        self,
        action_id: str,
        action: ActionDescriptor,
        *,
        confirmed: bool = False,
    ) -> AuthorizationDecision:
        self.verify_identity(action.subject_id)
        self.check_emergency_stop()

        with self._exclusive_state():
            self.check_emergency_stop()
            pending, authorized = self._load_actions()
            if action_id in authorized:
                return AuthorizationDecision(
                    authorized=False,
                    action_id=action_id,
                    reason="duplicate action_id already authorized",
                )

            if action.action_class not in SENSITIVE_ACTION_CLASSES:
                authorized.add(action_id)
                self._save_actions(pending, authorized)
                return AuthorizationDecision(
                    authorized=True, action_id=action_id, reason="not sensitive"
                )

            existing = pending.get(action_id)
            if not confirmed:
                if existing is not None and existing != action:
                    return AuthorizationDecision(
                        authorized=False,
                        action_id=action_id,
                        reason="action_id already awaits confirmation for a different action",
                    )
                pending[action_id] = action
                self._save_actions(pending, authorized)
                return AuthorizationDecision(
                    authorized=False,
                    action_id=action_id,
                    reason="owner confirmation required",
                )

            if existing is None or existing != action:
                return AuthorizationDecision(
                    authorized=False,
                    action_id=action_id,
                    reason="confirmation does not match the requested action",
                )

            del pending[action_id]
            authorized.add(action_id)
            self._save_actions(pending, authorized)
            return AuthorizationDecision(
                authorized=True, action_id=action_id, reason="owner confirmed"
            )
