from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.quality.scope import PYTHON_QUALITY_PATHS

ROOT = Path(__file__).resolve().parents[3]
BASELINE_PATH = ROOT / "operations" / "quality_baseline.json"
ERROR_LINE = re.compile(r"^(.+):\d+(?::\d+)?: error:.*\[([^\]]+)\]$", re.MULTILINE)


def main() -> int:
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    budget = int(baseline["mypy_error_budget"])
    raw_limits = baseline.get("mypy_error_budget_by_file_and_code", {})
    if not isinstance(raw_limits, dict):
        print("Invalid mypy baseline: mypy_error_budget_by_file_and_code must be an object.")
        return 1
    limits = {str(key): int(value) for key, value in raw_limits.items()}
    command = [
        sys.executable,
        "-m",
        "mypy",
        *PYTHON_QUALITY_PATHS,
        "--show-error-codes",
        "--no-error-summary",
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    output = result.stdout + result.stderr
    print(output, end="")
    errors = Counter(f"{path}|{code}" for path, code in ERROR_LINE.findall(output))
    error_count = sum(errors.values())

    if result.returncode not in {0, 1} or (result.returncode == 1 and error_count == 0):
        print(f"Mypy tool failure: exit code {result.returncode} produced no countable result.")
        return 1

    if error_count > budget:
        print(f"Mypy regression: {error_count} errors exceeds baseline budget {budget}.")
        return 1

    regressions = {
        key: (count, limits.get(key, 0))
        for key, count in sorted(errors.items())
        if count > limits.get(key, 0)
    }
    if regressions:
        print("Mypy regression by file/error code:")
        for key, (count, limit) in regressions.items():
            print(f"  {key}: {count} exceeds baseline {limit}")
        return 1

    if error_count:
        print(
            f"Mypy baseline preserved: {error_count}/{budget} existing errors. "
            "The gate allows no total or per-file/error-code increase; reduce the baseline "
            "when debt is fixed."
        )
    else:
        print("Mypy passed with zero errors. Set mypy_error_budget to 0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
