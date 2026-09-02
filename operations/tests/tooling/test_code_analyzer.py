"""Unit tests for the only finding class code_analyzer.py can fail on.

Before the 2026-09-02 checker review both tests in this file exercised an
`UnusedDetector` that duplicated Ruff's F401 and could never fail the gate,
while `StubDetector` — whose high-severity findings are exactly what makes
`main()` return 1 — had none. The detector is gone; the coverage moved to
the branch that blocks.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from operations.scripts.quality.code_analyzer import analyze_file


class StubDetectionTests(unittest.TestCase):
    def _analyze(self, source: str) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text(source, encoding="utf-8")
            return analyze_file(path)

    def _stubs(self, source: str) -> list[dict[str, object]]:
        stubs = self._analyze(source)["stubs"]
        assert isinstance(stubs, list)
        return stubs

    def test_pass_only_function_is_a_high_severity_stub(self) -> None:
        stubs = self._stubs("def unfinished():\n    pass\n")
        self.assertEqual([s["type"] for s in stubs], ["pass_only"])
        self.assertEqual(stubs[0]["severity"], "high")
        self.assertEqual(stubs[0]["function"], "unfinished")

    def test_not_implemented_function_is_a_high_severity_stub(self) -> None:
        stubs = self._stubs("def unfinished():\n    raise NotImplementedError()\n")
        self.assertEqual([s["type"] for s in stubs], ["not_implemented"])
        self.assertEqual(stubs[0]["severity"], "high")

    def test_async_stub_is_detected_the_same_as_a_sync_one(self) -> None:
        stubs = self._stubs("async def unfinished():\n    pass\n")
        self.assertEqual([s["type"] for s in stubs], ["pass_only"])

    def test_empty_with_block_is_medium_not_high(self) -> None:
        # Severity matters: only high-severity findings make main() exit 1.
        stubs = self._stubs("def f(ctx):\n    with ctx:\n        pass\n    return 1\n")
        self.assertEqual([s["type"] for s in stubs], ["empty_with_block"])
        self.assertEqual(stubs[0]["severity"], "medium")

    def test_pass_inside_a_branch_is_not_a_stub(self) -> None:
        # The reason this check is AST-based rather than a regex for `pass`.
        source = "def real(flag):\n    if flag:\n        pass\n    return flag\n"
        self.assertEqual(self._stubs(source), [])

    def test_raising_another_exception_is_not_a_stub(self) -> None:
        self.assertEqual(self._stubs("def real():\n    raise ValueError('bad')\n"), [])

    def test_todo_in_a_docstring_is_reported_without_being_a_stub(self) -> None:
        result = self._analyze('def real():\n    """TODO: tighten this."""\n    return 1\n')
        todos = result["todos"]
        assert isinstance(todos, list)
        self.assertEqual([t["function"] for t in todos], ["real"])
        self.assertEqual(result["stubs"], [])

    def test_unparseable_file_reports_an_error_instead_of_raising(self) -> None:
        result = self._analyze("def broken(:\n")
        self.assertIn("error", result)
        self.assertNotIn("stubs", result)


if __name__ == "__main__":
    unittest.main()
