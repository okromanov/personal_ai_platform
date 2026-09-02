import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from operations.scripts.quality import run_mypy_baseline


class MypyBaselineTests(unittest.TestCase):
    def _baseline(self, budget: int, limits: dict[str, int] | None = None) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        temp_dir = Path(temp.name)
        path = temp_dir / "quality_baseline.json"
        path.write_text(
            json.dumps(
                {
                    "mypy_error_budget": budget,
                    "mypy_error_budget_by_file_and_code": limits or {},
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_allows_existing_debt_at_or_below_budget(self) -> None:
        output = "a.py:1: error: one  [arg-type]\nb.py:2: error: two  [index]\n"
        completed = CompletedProcess([], 1, stdout=output, stderr="")
        with (
            patch.object(
                run_mypy_baseline,
                "BASELINE_PATH",
                self._baseline(2, {"a.py|arg-type": 1, "b.py|index": 1}),
            ),
            patch.object(run_mypy_baseline.subprocess, "run", return_value=completed),
        ):
            self.assertEqual(run_mypy_baseline.main(), 0)

    def test_blocks_error_count_increase(self) -> None:
        output = "a.py:1: error: one  [arg-type]\nb.py:2: error: two  [index]\n"
        completed = CompletedProcess([], 1, stdout=output, stderr="")
        with (
            patch.object(run_mypy_baseline, "BASELINE_PATH", self._baseline(1)),
            patch.object(run_mypy_baseline.subprocess, "run", return_value=completed),
        ):
            self.assertEqual(run_mypy_baseline.main(), 1)

    def test_blocks_new_error_code_even_when_total_is_unchanged(self) -> None:
        output = "a.py:1: error: one  [index]\n"
        completed = CompletedProcess([], 1, stdout=output, stderr="")
        with (
            patch.object(
                run_mypy_baseline,
                "BASELINE_PATH",
                self._baseline(1, {"a.py|arg-type": 1}),
            ),
            patch.object(run_mypy_baseline.subprocess, "run", return_value=completed),
        ):
            self.assertEqual(run_mypy_baseline.main(), 1)

    def test_blocks_tool_failure_without_countable_errors(self) -> None:
        completed = CompletedProcess([], 2, stdout="", stderr="invalid mypy configuration\n")
        with (
            patch.object(run_mypy_baseline, "BASELINE_PATH", self._baseline(201)),
            patch.object(run_mypy_baseline.subprocess, "run", return_value=completed),
        ):
            self.assertEqual(run_mypy_baseline.main(), 1)


class CommittedBaselineRatchetTests(unittest.TestCase):
    """`run_mypy_baseline.py` enforces the budget it is given — it cannot
    notice that the budget itself was raised. AGENTS.md §5.1 forbids widening
    a baseline instead of fixing the cause, and quality_baseline.json states
    "Debt may only decrease", but until this test nothing held the committed
    file to either: editing one number turned the gate green.

    Lowering the numbers below is always allowed. Raising one is a deliberate
    owner decision that has to change this test too, in the same commit,
    where a reviewer sees it.
    """

    def _committed(self) -> dict[str, object]:
        root = Path(__file__).resolve().parents[3]
        raw = (root / "operations" / "quality_baseline.json").read_text(encoding="utf-8")
        return dict(json.loads(raw))

    def test_total_error_budget_stays_at_zero(self) -> None:
        self.assertEqual(self._committed()["mypy_error_budget"], 0)

    def test_no_per_file_or_per_code_exemptions_are_carried(self) -> None:
        self.assertEqual(self._committed()["mypy_error_budget_by_file_and_code"], {})
