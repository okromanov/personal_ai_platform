"""CLI wrapper around recover_stale_sensitive_action_lock (AUD-013).

The recovery function itself is covered by
`operations/tests/product/test_owner_control.py::StaleLockRecoveryTests`.
What is covered here is the thin layer the runbook actually tells the owner
to run: argument parsing, and — the part that matters operationally — that a
refusal surfaces as a non-zero exit code on stderr rather than a traceback
or a misleading success message.
"""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from operations.scripts.owner_control import recover_lock
from src.owner_control import RECOVERY_CONFIRMATION_PHRASE


class RecoverLockCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state_dir = Path(self._tmp.name)
        self.lock_path = self.state_dir / "owner_control_actions.lock"

    def _run(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["recover_lock", *argv]),
            redirect_stdout(out),
            redirect_stderr(err),
        ):
            code = recover_lock.main()
        return code, out.getvalue(), err.getvalue()

    def test_removes_a_stale_lock_and_reports_the_path(self) -> None:
        self.lock_path.mkdir(parents=True)
        code, stdout, _ = self._run(str(self.state_dir), "--confirm", RECOVERY_CONFIRMATION_PHRASE)
        self.assertEqual(code, 0)
        self.assertIn("owner_control_actions.lock", stdout)
        self.assertFalse(self.lock_path.exists())

    def test_refusal_becomes_exit_1_on_stderr_and_leaves_the_lock(self) -> None:
        self.lock_path.mkdir(parents=True)
        code, stdout, stderr = self._run(str(self.state_dir), "--confirm", "yes please")
        self.assertEqual(code, 1)
        self.assertIn("ERROR:", stderr)
        self.assertEqual(stdout, "")
        self.assertTrue(self.lock_path.is_dir(), "отказ не должен снимать блокировку")

    def test_missing_confirmation_flag_is_rejected_by_the_parser(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            self._run(str(self.state_dir))
        self.assertNotEqual(raised.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
