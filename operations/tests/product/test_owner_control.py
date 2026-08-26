"""Unit tests for the Owner Control component (ARC_CMP_002)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.owner_control import (
    ActionClass,
    ActionDescriptor,
    EmergencyStopActive,
    EmergencySwitch,
    EmergencySwitchStateError,
    IdentityRejected,
    OwnerControlGate,
    OwnerControlStateError,
)


def _action(
    action_class: ActionClass = ActionClass.DESTRUCTIVE,
    *,
    subject_id: str = "owner_1",
    capability_name: str = "files.delete",
    resource: str = "file_a",
    params: dict[str, object] | None = None,
) -> ActionDescriptor:
    return ActionDescriptor.create(
        subject_id=subject_id,
        capability_name=capability_name,
        resource=resource,
        action_class=action_class,
        params=params or {},
    )


class OwnerControlGateInitTests(unittest.TestCase):
    def test_rejects_empty_owner_subject_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                OwnerControlGate(owner_subject_id="", state_dir=Path(tmp))


class OwnerControlGateIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.gate = OwnerControlGate(owner_subject_id="owner_1", state_dir=Path(self._tmp.name))

    def test_accepts_the_recognized_owner(self) -> None:
        self.gate.verify_identity("owner_1")

    def test_rejects_any_other_subject(self) -> None:
        with self.assertRaises(IdentityRejected):
            self.gate.verify_identity("impostor")

    def test_action_authorization_rechecks_identity(self) -> None:
        with self.assertRaises(IdentityRejected):
            self.gate.authorize_sensitive_action("action", _action(subject_id="impostor"))


class OwnerControlGateEmergencySwitchTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state_dir = Path(self._tmp.name)
        self.gate = OwnerControlGate(owner_subject_id="owner_1", state_dir=self.state_dir)

    def test_fresh_deployment_is_not_stopped(self) -> None:
        self.gate.check_emergency_stop()

    def test_activate_blocks_new_operations(self) -> None:
        self.gate.emergency_switch.activate(reason="owner requested stop")
        with self.assertRaises(EmergencyStopActive):
            self.gate.check_emergency_stop()

    def test_deactivate_clears_the_block(self) -> None:
        self.gate.emergency_switch.activate()
        self.gate.emergency_switch.deactivate()
        self.gate.check_emergency_stop()

    def test_switch_survives_process_restart(self) -> None:
        self.gate.emergency_switch.activate(reason="restart test")
        restarted_gate = OwnerControlGate(owner_subject_id="owner_1", state_dir=self.state_dir)
        with self.assertRaises(EmergencyStopActive):
            restarted_gate.check_emergency_stop()

    def test_active_switch_blocks_action_authorization(self) -> None:
        self.gate.emergency_switch.activate()
        with self.assertRaises(EmergencyStopActive):
            self.gate.authorize_sensitive_action("action", _action())

    def test_corrupt_switch_state_causes_safe_stop(self) -> None:
        self.gate.emergency_switch._path.write_text("not json", encoding="utf-8")
        with self.assertRaises(EmergencyStopActive):
            self.gate.check_emergency_stop()


class EmergencySwitchDirectTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.switch = EmergencySwitch(Path(self._tmp.name) / "switch.json")

    def test_missing_state_file_reads_as_inactive(self) -> None:
        self.assertFalse(self.switch.is_active())

    def test_corrupted_state_file_fails_closed(self) -> None:
        self.switch._path.write_text("not json", encoding="utf-8")
        with self.assertRaises(EmergencySwitchStateError):
            self.switch.is_active()

    def test_non_boolean_state_fails_closed(self) -> None:
        self.switch._path.write_text(json.dumps({"active": "no"}), encoding="utf-8")
        with self.assertRaises(EmergencySwitchStateError):
            self.switch.is_active()

    def test_activate_then_deactivate_round_trips(self) -> None:
        self.switch.activate(reason="test")
        self.assertTrue(self.switch.is_active())
        self.switch.deactivate()
        self.assertFalse(self.switch.is_active())

    def test_atomic_write_leaves_no_temporary_file(self) -> None:
        self.switch.activate(reason="atomic")
        leftovers = list(self.switch._path.parent.glob(f".{self.switch._path.name}.*.tmp"))
        self.assertEqual(leftovers, [])


class OwnerControlGateSensitiveActionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state_dir = Path(self._tmp.name)
        self.gate = OwnerControlGate(owner_subject_id="owner_1", state_dir=self.state_dir)

    def test_read_action_is_authorized_immediately(self) -> None:
        decision = self.gate.authorize_sensitive_action(
            "action_1", _action(ActionClass.READ, capability_name="files.read")
        )
        self.assertTrue(decision.authorized)

    def test_sensitive_action_requires_confirmation(self) -> None:
        decision = self.gate.authorize_sensitive_action("action_2", _action())
        self.assertFalse(decision.authorized)
        self.assertEqual(decision.reason, "owner confirmation required")

    def test_matching_descriptor_is_authorized(self) -> None:
        action = _action(params={"recursive": False})
        self.gate.authorize_sensitive_action("action_3", action)
        decision = self.gate.authorize_sensitive_action("action_3", action, confirmed=True)
        self.assertTrue(decision.authorized)

    def test_parameter_order_does_not_change_descriptor(self) -> None:
        first = _action(params={"a": 1, "b": 2})
        reordered = _action(params={"b": 2, "a": 1})
        self.gate.authorize_sensitive_action("action_4", first)
        decision = self.gate.authorize_sensitive_action("action_4", reordered, confirmed=True)
        self.assertTrue(decision.authorized)

    def test_confirmation_with_different_resource_is_rejected(self) -> None:
        self.gate.authorize_sensitive_action("action_5", _action(resource="file_a"))
        decision = self.gate.authorize_sensitive_action(
            "action_5", _action(resource="file_b"), confirmed=True
        )
        self.assertFalse(decision.authorized)
        self.assertEqual(decision.reason, "confirmation does not match the requested action")

    def test_confirmation_with_different_capability_is_rejected(self) -> None:
        self.gate.authorize_sensitive_action("action_6", _action(capability_name="files.delete"))
        decision = self.gate.authorize_sensitive_action(
            "action_6", _action(capability_name="mail.send"), confirmed=True
        )
        self.assertFalse(decision.authorized)

    def test_unconfirmed_action_id_cannot_be_rebound(self) -> None:
        self.gate.authorize_sensitive_action("action_7", _action(resource="file_a"))
        decision = self.gate.authorize_sensitive_action("action_7", _action(resource="file_b"))
        self.assertFalse(decision.authorized)
        self.assertIn("different action", decision.reason)

    def test_confirmation_without_prior_request_is_rejected(self) -> None:
        decision = self.gate.authorize_sensitive_action(
            "never_requested", _action(ActionClass.ADMIN), confirmed=True
        )
        self.assertFalse(decision.authorized)

    def test_duplicate_action_id_is_rejected_after_restart(self) -> None:
        action = _action()
        self.gate.authorize_sensitive_action("action_8", action)
        first = self.gate.authorize_sensitive_action("action_8", action, confirmed=True)
        restarted = OwnerControlGate(owner_subject_id="owner_1", state_dir=self.state_dir)
        replay = restarted.authorize_sensitive_action("action_8", action, confirmed=True)
        self.assertTrue(first.authorized)
        self.assertFalse(replay.authorized)
        self.assertEqual(replay.reason, "duplicate action_id already authorized")

    def test_pending_confirmation_survives_restart(self) -> None:
        action = _action()
        self.gate.authorize_sensitive_action("action_9", action)
        restarted = OwnerControlGate(owner_subject_id="owner_1", state_dir=self.state_dir)
        decision = restarted.authorize_sensitive_action("action_9", action, confirmed=True)
        self.assertTrue(decision.authorized)

    def test_corrupt_action_ledger_fails_closed(self) -> None:
        self.gate._actions_path.write_text("not json", encoding="utf-8")
        with self.assertRaises(OwnerControlStateError):
            self.gate.authorize_sensitive_action("action_10", _action())

    def test_existing_lock_fails_closed(self) -> None:
        self.gate._actions_lock_path.mkdir(parents=True)
        with self.assertRaises(OwnerControlStateError):
            self.gate.authorize_sensitive_action("action_11", _action())


if __name__ == "__main__":
    unittest.main()
