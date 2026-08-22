from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import find_project_root, run_command

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def load_policy(root: Path) -> dict[str, object]:
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    try:
        policy = data["tool"]["personal_ai_platform"]["coverage"]
    except (KeyError, TypeError) as exc:
        raise ValueError("Отсутствует tool.personal_ai_platform.coverage") from exc
    if not isinstance(policy, dict):
        raise ValueError("Coverage policy должна быть TOML table")
    return policy


def parse_changed_lines(diff: str) -> dict[str, set[int]]:
    result: dict[str, set[int]] = {}
    current: str | None = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line.removeprefix("+++ b/")
            result.setdefault(current, set())
            continue
        match = HUNK.match(line)
        if current is None or match is None:
            continue
        start = int(match.group(1))
        count = int(match.group(2) or "1")
        result[current].update(range(start, start + count))
    return result


def changed_lines(root: Path, base: str) -> dict[str, set[int]]:
    result = run_command(
        [
            "git",
            "diff",
            "--no-ext-diff",
            "--unified=0",
            "--diff-filter=ACMR",
            f"{base}..HEAD",
            "--",
            "operations/scripts",
        ],
        cwd=root,
    )
    if not result.ok:
        raise ValueError(f"Не удалось вычислить diff coverage относительно {base}: {result.stderr}")
    return parse_changed_lines(result.stdout)


def evaluate_coverage(
    report: dict[str, object],
    policy: dict[str, object],
    additions: dict[str, set[int]] | None = None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    rows: list[str] = []
    totals = report.get("totals", {})
    files = report.get("files", {})
    if (
        "totals" not in report
        or "files" not in report
        or not isinstance(totals, dict)
        or not isinstance(files, dict)
    ):
        return ["Coverage JSON не содержит totals/files"], rows

    overall = float(cast(float | int | str, totals.get("percent_covered", 0)))
    overall_floor = float(cast(float | int | str, policy.get("overall", 75)))
    rows.append(f"overall: {overall:.2f}% (minimum {overall_floor:.2f}%)")
    if overall < overall_floor:
        errors.append(f"Общее покрытие {overall:.2f}% ниже {overall_floor:.2f}%")

    modules = policy.get("modules", {})
    if not isinstance(modules, dict):
        errors.append("Coverage policy modules должна быть TOML table")
        modules = {}
    for path, raw_floor in sorted(modules.items()):
        file_data = files.get(str(path))
        if not isinstance(file_data, dict) or not isinstance(file_data.get("summary"), dict):
            errors.append(f"Критический модуль отсутствует в coverage JSON: {path}")
            continue
        actual = float(cast(float | int | str, file_data["summary"].get("percent_covered", 0)))
        floor = float(cast(float | int | str, raw_floor))
        rows.append(f"{path}: {actual:.2f}% (minimum {floor:.2f}%)")
        if actual < floor:
            errors.append(f"{path}: покрытие {actual:.2f}% ниже {floor:.2f}%")

    if additions is not None:
        executable = 0
        covered = 0
        for path, lines in additions.items():
            file_data = files.get(path)
            if not isinstance(file_data, dict):
                if lines:
                    errors.append(f"Изменённый Python-модуль отсутствует в coverage JSON: {path}")
                continue
            executed = {int(value) for value in file_data.get("executed_lines", [])}
            missing = {int(value) for value in file_data.get("missing_lines", [])}
            measurable = lines & (executed | missing)
            executable += len(measurable)
            covered += len(measurable & executed)
        actual_diff = 100.0 if executable == 0 else covered * 100.0 / executable
        diff_floor = float(cast(float | int | str, policy.get("diff", 90)))
        rows.append(
            f"changed lines: {covered}/{executable} = {actual_diff:.2f}% "
            f"(minimum {diff_floor:.2f}%)"
        )
        if actual_diff < diff_floor:
            errors.append(
                f"Покрытие изменённых исполняемых строк {actual_diff:.2f}% ниже {diff_floor:.2f}%"
            )
    return errors, rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Check aggregate, critical and diff coverage")
    parser.add_argument("--coverage-json", default="runtime/coverage.json")
    parser.add_argument("--base", help="Git base revision for changed-line coverage")
    parser.add_argument("--skip-diff", action="store_true")
    args = parser.parse_args()

    root = find_project_root(Path.cwd())
    report_path = Path(args.coverage_json)
    if not report_path.is_absolute():
        report_path = root / report_path
    if not report_path.is_file():
        print(f"ERROR: coverage JSON отсутствует: {report_path}")
        return 1
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        policy = load_policy(root)
        additions = None if args.skip_diff else changed_lines(root, args.base or "HEAD^")
        errors, rows = evaluate_coverage(report, policy, additions)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print("Coverage policy:")
    for row in rows:
        print(f"  {row}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Coverage policy passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
