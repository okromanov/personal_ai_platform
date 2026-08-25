"""Unit tests for the Owner Control component (ARC_CMP_002).

Runs under the canonical `operations/scripts/quality/run_unittests.py`
discovery, so it is part of the enforced CI gate.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.owner_control import (
    ActionClass,
    EmergencyStopActive,
    EmergencySwitch,
    IdentityRejected,
    OwnerControlGate,
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
        self.gate.verify_identity("owner_1")  # must not raise

    def test_rejects_any_other_subject(self) -> None:
        with self.assertRaises(IdentityRejected):
            self.gate.verify_identity("impostor")

    def test_rejects_empty_subject(self) -> None:
        with self.assertRaises(IdentityRejected):
            self.gate.verify_identity("")


class OwnerControlGateEmergencySwitchTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state_dir = Path(self._tmp.name)
        self.gate = OwnerControlGate(owner_subject_id="owner_1", state_dir=self.state_dir)

    def test_fresh_deployment_is_not_stopped(self) -> None:
        self.gate.check_emergency_stop()  # must not raise

    def test_activate_blocks_new_operations(self) -> None:
        self.gate.emergency_switch.activate(reason="owner requested stop")
        with self.assertRaises(EmergencyStopActive):
            self.gate.check_emergency_stop()

    def test_deactivate_clears_the_block(self) -> None:
        self.gate.emergency_switch.activate()
        self.gate.emergency_switch.deactivate()
        self.gate.check_emergency_stop()  # must not raise

    def test_switch_survives_process_restart(self) -> None:
        self.gate.emergency_switch.activate(reason="restart test")

        restarted_gate = OwnerControlGate(owner_subject_id="owner_1", state_dir=self.state_dir)

        with self.assertRaises(EmergencyStopActive):
            restarted_gate.check_emergency_stop()

    def test_switch_is_independent_of_model_or_runtime_object(self) -> None:
        # The switch is read from disk, not from in-memory runtime/model state,
        # so a brand-new gate instance sees the same persisted state.
        self.gate.emergency_switch.activate()
        other_view = EmergencySwitch(self.state_dir / "emergency_switch.json")
        self.assertTrue(other_view.is_active())


class EmergencySwitchDirectTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.switch = EmergencySwitch(Path(self._tmp.name) / "switch.json")

    def test_missing_state_file_reads_as_inactive(self) -> None:
        self.assertFalse(self.switch.is_active())

    def test_corrupted_state_file_reads_as_inactive(self) -> None:
        self.switch._path.parent.mkdir(parents=True, exist_ok=True)
        self.switch._path.write_text("not json", encoding="utf-8")
        self.assertFalse(self.switch.is_active())

    def test_activate_then_deactivate_round_trips(self) -> None:
        self.switch.activate(reason="test")
        self.assertTrue(self.switch.is_active())
        self.switch.deactivate()
        self.assertFalse(self.switch.is_active())


class OwnerControlGateSensitiveActionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.gate = OwnerControlGate(owner_subject_id="owner_1", state_dir=Path(self._tmp.name))

    def test_read_action_is_authorized_immediately(self) -> None:
        decision = self.gate.authorize_sensitive_action(
            "action_1", ActionClass.READ, {"query": "status"}
        )
        self.assertTrue(decision.authorized)

    def test_sensitive_action_without_confirmation_is_rejected(self) -> None:
        decision = self.gate.authorize_sensitive_action(
            "action_2", ActionClass.WRITE_EXTERNAL, {"to": "owner@example.com"}
        )
        self.assertFalse(decision.authorized)
        self.assertEqual(decision.reason, "owner confirmation required")

    def test_confirmed_sensitive_action_with_matching_params_is_authorized(self) -> None:
        params = {"to": "owner@example.com", "body": "hello"}
        self.gate.authorize_sensitive_action("action_3", ActionClass.WRITE_EXTERNAL, params)

        decision = self.gate.authorize_sensitive_action(
            "action_3", ActionClass.WRITE_EXTERNAL, params, confirmed=True
        )
        self.assertTrue(decision.authorized)

    def test_confirmation_with_different_params_is_rejected(self) -> None:
        self.gate.authorize_sensitive_action(
            "action_4", ActionClass.DESTRUCTIVE, {"target": "file_a"}
        )

        decision = self.gate.authorize_sensitive_action(
            "action_4", ActionClass.DESTRUCTIVE, {"target": "file_b"}, confirmed=True
        )
        self.assertFalse(decision.authorized)
        self.assertEqual(decision.reason, "confirmation does not match the requested action")

    def test_confirmation_without_prior_request_is_rejected(self) -> None:
        decision = self.gate.authorize_sensitive_action(
            "never_requested", ActionClass.ADMIN, {"cmd": "restart"}, confirmed=True
        )
        self.assertFalse(decision.authorized)

    def test_duplicate_action_id_is_rejected_after_authorization(self) -> None:
        params = {"target": "file_a"}
        self.gate.authorize_sensitive_action("action_5", ActionClass.DESTRUCTIVE, params)
        first = self.gate.authorize_sensitive_action(
            "action_5", ActionClass.DESTRUCTIVE, params, confirmed=True
        )
        self.assertTrue(first.authorized)

        replay = self.gate.authorize_sensitive_action(
            "action_5", ActionClass.DESTRUCTIVE, params, confirmed=True
        )
        self.assertFalse(replay.authorized)
        self.assertEqual(replay.reason, "duplicate action_id already authorized")

    def test_duplicate_read_action_id_is_also_rejected(self) -> None:
        self.gate.authorize_sensitive_action("action_6", ActionClass.READ, {})
        replay = self.gate.authorize_sensitive_action("action_6", ActionClass.READ, {})
        self.assertFalse(replay.authorized)


if __name__ == "__main__":
    unittest.main()
