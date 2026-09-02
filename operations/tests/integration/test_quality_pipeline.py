"""Contract test for the one quality tool this repository owns.

Scope note (2026-09-02 review). This file used to also run Ruff, Bandit,
mypy and Vulture as subprocesses. Those checks are already blocking steps of
`operations/scripts/quality/run_suite.py` — the canonical gate that both
`pre_push_hook.sh` and the `quality-skills` CI job execute — so re-running
them inside the unit-test step bought nothing but runtime. Worse, four of
the assertions were vacuous: they asserted `returncode in [0, 1]`, which is
exactly the pair of exit codes each of those tools returns for "clean" and
"found problems". A probe file carrying real F401/F841 violations, a real
`import-not-found` mypy error and a real `subprocess.call(..., shell=True)`
Bandit finding left every one of them green while the corresponding
run_suite.py step went red. A test that cannot distinguish a clean tree from
a dirty one is not coverage of the tool; the blocking step is.

`code_analyzer.py`, by contrast, is this repository's own script, and
`record_quality_suite.py` records its stdout as evidence, so the JSON
contract it emits is worth pinning here at the CLI boundary. Its analysis
logic is unit-tested in `operations/tests/tooling/test_code_analyzer.py`.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


class CodeAnalyzerCliContractTest(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[3]

    def _run(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "operations/scripts/quality/code_analyzer.py"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

    def test_emits_the_json_shape_recorded_as_evidence(self) -> None:
        result = self._run()
        report = json.loads(result.stdout)
        self.assertIn("findings", report)
        summary = report["summary"]
        self.assertIn("files_analyzed", summary)
        self.assertIn("critical_issues", summary)
        self.assertGreater(summary["files_analyzed"], 0)

    def test_runs_clean_against_this_repository(self) -> None:
        result = self._run()
        # Not `in (0, 1)`: exit 1 means a high-severity stub was found, and
        # the tree is expected to carry none. Asserting the pair would make
        # this test pass whether or not the repository is actually clean.
        self.assertEqual(result.returncode, 0, result.stdout[-2000:])
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
