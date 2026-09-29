"""Unit tests for the Owner Control component (ARC_CMP_002)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from os import name as os_name
from pathlib import Path
from unittest import mock

from src.owner_control import (
    RECOVERY_CONFIRMATION_PHRASE,
    ActionClass,
    ActionDescriptor,
    EmergencyStopActive,
    EmergencySwitch,
    EmergencySwitchStateError,
    IdentityRejected,
    OwnerControlGate,
    OwnerControlStateError,
    StaleLockRecoveryError,
    recover_stale_sensitive_action_lock,
)
from src.owner_control import control as control_module
from src.owner_control.state_io import atomic_write_json


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

    def test_atomic_write_fsyncs_parent_after_replace(self) -> None:
        target = self.switch._path
        events: list[str] = []
        real_replace = os.replace
        real_fsync = os.fsync

        def recording_replace(source: str | Path, destination: str | Path) -> None:
            real_replace(source, destination)
            events.append("replace")

        def recording_fsync(descriptor: int) -> None:
            real_fsync(descriptor)
            events.append("fsync")

        with (
            mock.patch("src.owner_control.state_io.os.replace", side_effect=recording_replace),
            mock.patch("src.owner_control.state_io.os.fsync", side_effect=recording_fsync),
        ):
            atomic_write_json(target, {"active": True})

        expected = ["fsync", "replace"] if os_name == "nt" else ["fsync", "replace", "fsync"]
        self.assertEqual(events, expected)

    def test_directory_fsync_failure_is_not_reported_as_success(self) -> None:
        target = self.switch._path
        if os_name == "nt":
            atomic_write_json(target, {"active": True})
            self.assertTrue(target.is_file())
            return
        real_fsync = os.fsync
        calls = 0

        def fail_second_fsync(descriptor: int) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated directory durability failure")
            real_fsync(descriptor)

        with mock.patch("src.owner_control.state_io.os.fsync", side_effect=fail_second_fsync):
            with self.assertRaisesRegex(OSError, "directory durability"):
                atomic_write_json(target, {"active": True})


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

    def test_lock_holder_metadata_is_recorded_and_cleared(self) -> None:
        holder_path = self.gate._actions_lock_path / "holder.json"
        with self.gate._exclusive_state():
            recorded = json.loads(holder_path.read_text(encoding="utf-8"))
            self.assertEqual(recorded["pid"], os.getpid())
            self.assertIn("acquired_at", recorded)
        self.assertFalse(self.gate._actions_lock_path.exists())


class StaleLockRecoveryTests(unittest.TestCase):
    """AUD-013: a process that crashes between os.mkdir and os.rmdir leaves
    the sensitive-action lock held forever. recover_stale_sensitive_action_lock()
    is the explicit, owner-invoked recovery path -- never automatic, and it
    must refuse whenever it cannot prove the holder is actually dead."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state_dir = Path(self._tmp.name)
        self.lock_path = self.state_dir / "owner_control_actions.lock"

    def test_refuses_without_the_exact_confirmation_phrase(self) -> None:
        self.lock_path.mkdir(parents=True)
        with self.assertRaises(StaleLockRecoveryError):
            recover_stale_sensitive_action_lock(self.state_dir, confirmation="yes please")
        self.assertTrue(self.lock_path.is_dir())

    def test_refuses_when_no_lock_is_held(self) -> None:
        with self.assertRaises(StaleLockRecoveryError):
            recover_stale_sensitive_action_lock(
                self.state_dir, confirmation=RECOVERY_CONFIRMATION_PHRASE
            )

    def test_refuses_when_holder_process_is_still_alive(self) -> None:
        self.lock_path.mkdir(parents=True)
        atomic_write_json(
            self.lock_path / "holder.json", {"pid": 4242, "acquired_at": "2026-08-29T00:00:00Z"}
        )
        with self.assertRaises(StaleLockRecoveryError):
            recover_stale_sensitive_action_lock(
                self.state_dir,
                confirmation=RECOVERY_CONFIRMATION_PHRASE,
                is_process_alive=lambda _pid: True,
            )
        self.assertTrue(self.lock_path.is_dir())

    def test_removes_the_lock_when_holder_process_is_confirmed_dead(self) -> None:
        self.lock_path.mkdir(parents=True)
        atomic_write_json(
            self.lock_path / "holder.json", {"pid": 4242, "acquired_at": "2026-08-29T00:00:00Z"}
        )
        recover_stale_sensitive_action_lock(
            self.state_dir,
            confirmation=RECOVERY_CONFIRMATION_PHRASE,
            is_process_alive=lambda _pid: False,
        )
        self.assertFalse(self.lock_path.exists())

    def test_removes_a_lock_with_no_holder_metadata(self) -> None:
        self.lock_path.mkdir(parents=True)
        recover_stale_sensitive_action_lock(
            self.state_dir, confirmation=RECOVERY_CONFIRMATION_PHRASE
        )
        self.assertFalse(self.lock_path.exists())


class ProcessIsAliveTests(unittest.TestCase):
    """AUD-051: _process_is_alive must be platform-safe and fail-closed."""

    def test_posix_dead_process_returns_false(self) -> None:
        if os_name == "nt":
            return
        with mock.patch("os.kill", side_effect=ProcessLookupError):
            self.assertFalse(control_module._process_is_alive(4242))

    def test_posix_permission_denied_returns_true(self) -> None:
        if os_name == "nt":
            return
        with mock.patch("os.kill", side_effect=PermissionError):
            self.assertTrue(control_module._process_is_alive(4242))

    def test_posix_no_exception_returns_true(self) -> None:
        if os_name == "nt":
            return
        with mock.patch("os.kill", return_value=None):
            self.assertTrue(control_module._process_is_alive(4242))

    def test_delegates_to_windows_helper_on_win32(self) -> None:
        with (
            mock.patch("sys.platform", "win32"),
            mock.patch.object(control_module, "_process_is_alive_windows", return_value=False),
        ):
            self.assertFalse(control_module._process_is_alive(4242))

    def test_windows_invalid_pid_returns_false(self) -> None:
        if os_name != "nt":
            return
        fake_kernel = mock.MagicMock()
        fake_kernel.OpenProcess.return_value = 0
        fake_kernel.GetLastError.return_value = 87  # ERROR_INVALID_PARAMETER
        with mock.patch("ctypes.windll.kernel32", fake_kernel):
            self.assertFalse(control_module._process_is_alive_windows(4242))

    def test_windows_access_denied_returns_true(self) -> None:
        if os_name != "nt":
            return
        fake_kernel = mock.MagicMock()
        fake_kernel.OpenProcess.return_value = 0
        fake_kernel.GetLastError.return_value = 5  # ERROR_ACCESS_DENIED
        with mock.patch("ctypes.windll.kernel32", fake_kernel):
            self.assertTrue(control_module._process_is_alive_windows(4242))

    def test_windows_still_active_returns_true(self) -> None:
        if os_name != "nt":
            return
        fake_kernel = mock.MagicMock()
        fake_kernel.OpenProcess.return_value = 12345
        fake_exit_code = mock.MagicMock()
        fake_exit_code.value = 259  # STILL_ACTIVE
        with (
            mock.patch("ctypes.windll.kernel32", fake_kernel),
            mock.patch("ctypes.c_ulong", return_value=fake_exit_code),
            mock.patch("ctypes.byref", return_value=fake_exit_code),
        ):
            self.assertTrue(control_module._process_is_alive_windows(4242))

    def test_windows_exited_returns_false(self) -> None:
        if os_name != "nt":
            return
        fake_kernel = mock.MagicMock()
        fake_kernel.OpenProcess.return_value = 12345
        fake_exit_code = mock.MagicMock()
        fake_exit_code.value = 0
        with (
            mock.patch("ctypes.windll.kernel32", fake_kernel),
            mock.patch("ctypes.c_ulong", return_value=fake_exit_code),
            mock.patch("ctypes.byref", return_value=fake_exit_code),
        ):
            self.assertFalse(control_module._process_is_alive_windows(4242))


if __name__ == "__main__":
    unittest.main()
