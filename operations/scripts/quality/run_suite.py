from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import tomllib
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import atomic_write, find_project_root

STEP_TIMINGS_PATH = "runtime/step_timings.json"


class QualityFailure(RuntimeError):
    pass


IGNORED_CONFIG_DIRS = {".git", ".venv", "node_modules", "runtime"}
EXACT_REQUIREMENT = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)==(?P<version>[A-Za-z0-9][A-Za-z0-9._+!-]*)$"
)
DEV_REQUIREMENTS_PATH = Path("operations/quality/requirements_dev.txt")
# Function parameters Vulture flags as unused (100% confidence) but that are
# kept intentionally: evidence_ref/semantic_review_ref preserve caller
# clarity in acceptance/apply.py's apply_acceptance() even though only their
# digests are persisted (local file paths aren't reproducible across
# machines); arch_count mirrors sibling generator signatures in
# requirements/requirement_wizard.py's generate_task_documents(), which
# iterates context.arch_components directly instead.
VULTURE_IGNORED_NAMES = "evidence_ref,semantic_review_ref,arch_count"


def _ignored_config_path(path: Path) -> bool:
    return bool(IGNORED_CONFIG_DIRS.intersection(path.parts))


def validate_json_files(root: Path) -> None:
    for path in sorted(root.rglob("*.json")):
        if _ignored_config_path(path):
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as exc:
            raise QualityFailure(f"Invalid JSON {path.relative_to(root)}: {exc}") from exc


def validate_toml_files(root: Path) -> None:
    for path in sorted(root.rglob("*.toml")):
        if _ignored_config_path(path):
            continue
        try:
            tomllib.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError, TypeError) as exc:
            raise QualityFailure(f"Invalid TOML {path.relative_to(root)}: {exc}") from exc


def validate_development_requirements(root: Path) -> None:
    path = root / DEV_REQUIREMENTS_PATH
    if not path.is_file():
        raise QualityFailure(f"Missing {DEV_REQUIREMENTS_PATH.as_posix()}")

    packages: dict[str, int] = {}
    pin_count = 0
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = EXACT_REQUIREMENT.fullmatch(line)
        if match is None:
            raise QualityFailure(
                f"{DEV_REQUIREMENTS_PATH.as_posix()}:{line_number}: "
                "dependency must use exact name==version pin"
            )
        normalized = re.sub(r"[-_.]+", "-", match.group("name")).lower()
        if normalized in packages:
            raise QualityFailure(
                f"{DEV_REQUIREMENTS_PATH.as_posix()}:{line_number}: duplicate dependency "
                f"{match.group('name')} (first declared on line {packages[normalized]})"
            )
        packages[normalized] = line_number
        pin_count += 1
    if pin_count == 0:
        raise QualityFailure(
            f"{DEV_REQUIREMENTS_PATH.as_posix()} must contain at least one pinned dependency"
        )


def validate_configuration_files(root: Path) -> None:
    validate_json_files(root)
    validate_toml_files(root)
    validate_development_requirements(root)


def validate_python_permissions(root: Path) -> None:
    if os.name == "nt":
        return
    executable = [
        path.relative_to(root).as_posix()
        for base in (root / "operations/scripts", root / "operations/tests")
        for path in base.rglob("*.py")
        if path.stat().st_mode & 0o111
    ]
    if executable:
        raise QualityFailure("Python files must not be executable: " + ", ".join(executable))


def _record_step_timing(root: Path, name: str, duration_seconds: float) -> None:
    """Persist how long `name` took, for owner_dashboard.py's repository stats.

    Best-effort: a write failure here must not fail the quality suite itself.
    """
    path = root / STEP_TIMINGS_PATH
    try:
        timings = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        if not isinstance(timings, dict):
            timings = {}
    except (OSError, ValueError):
        timings = {}
    timings[name] = round(duration_seconds, 3)
    atomic_write(path, json.dumps(timings, ensure_ascii=False, indent=2))


def run_step(
    root: Path,
    name: str,
    command: list[str],
    *,
    artifact: str | None = None,
) -> None:
    print(f"\n== {name} ==")
    start = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    _record_step_timing(root, name, time.perf_counter() - start)
    output = completed.stdout
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    if artifact:
        target = root / artifact
        target.parent.mkdir(parents=True, exist_ok=True)
        # A tool that succeeds with nothing to report (e.g. Vulture finding
        # no dead code) produces empty stdout. record_quality_suite.py
        # treats a zero-byte artifact as evidence the step never actually
        # ran, so an explicit marker keeps a clean result distinguishable
        # from a missing one.
        target.write_text(output or f"{name}: no output (clean run)\n", encoding="utf-8")
    if completed.returncode != 0:
        raise QualityFailure(f"{name} failed with exit code {completed.returncode}")


def run_fast(root: Path, python: str) -> None:
    validate_configuration_files(root)
    validate_python_permissions(root)
    run_step(
        root,
        "Python syntax",
        [python, "-m", "compileall", "-q", "operations/scripts", "operations/tests"],
    )
    run_step(
        root, "Fast repository checks", [python, "operations/scripts/documents/check.py", "--fast"]
    )
    run_step(
        root,
        "Ruff lint",
        [python, "-m", "ruff", "check", "operations/scripts", "operations/tests"],
    )
    run_step(
        root,
        "Unit tests",
        [python, "operations/scripts/quality/run_unittests.py"],
    )
    run_step(
        root,
        "Regenerate derived documents",
        [python, "operations/scripts/documents/generate.py", "--all"],
    )
    run_step(
        root,
        "Generated drift",
        ["git", "diff", "--exit-code", "--", "project_status.md", "tasks.md", "generated"],
    )


def run_full(root: Path, python: str, base: str | None) -> None:
    validate_configuration_files(root)
    validate_python_permissions(root)
    (root / "runtime").mkdir(exist_ok=True)
    run_step(
        root,
        "Regenerate derived documents",
        [python, "operations/scripts/documents/generate.py", "--all"],
    )
    run_step(
        root,
        "Documentation audit",
        [python, "operations/scripts/documents/check.py", "--all", "--json"],
        artifact="runtime/check_summary.json",
    )
    run_step(
        root,
        "Security audit (Bandit)",
        [
            python,
            "-m",
            "bandit",
            "-r",
            "operations/scripts",
            "--severity-level",
            "medium",
            "-f",
            "json",
            "-q",
        ],
        artifact="runtime/security_audit.json",
    )
    run_step(
        root,
        "Code quality analysis (AST)",
        [python, "operations/scripts/quality/code_analyzer.py"],
        artifact="runtime/code_analysis.json",
    )
    run_step(
        root,
        "Dead code detection (Vulture)",
        [
            python,
            "-m",
            "vulture",
            "operations/scripts",
            "operations/tests",
            "--min-confidence",
            "80",
            "--ignore-names",
            VULTURE_IGNORED_NAMES,
        ],
        artifact="runtime/dead_code.txt",
    )
    run_step(
        root,
        "Ruff lint",
        [
            python,
            "-m",
            "ruff",
            "check",
            "operations/scripts",
            "operations/tests",
            "--output-format",
            "concise",
        ],
        artifact="runtime/ruff_check.txt",
    )
    run_step(
        root,
        "Ruff format",
        [python, "-m", "ruff", "format", "operations/scripts", "operations/tests", "--check"],
        artifact="runtime/ruff_format.txt",
    )
    run_step(
        root,
        "Mypy regression",
        [python, "operations/scripts/quality/run_mypy_baseline.py"],
        artifact="runtime/mypy_baseline.txt",
    )
    run_step(root, "Coverage reset", [python, "-m", "coverage", "erase"])
    run_step(
        root,
        "Unit tests with branch coverage",
        [
            python,
            "-m",
            "coverage",
            "run",
            "operations/scripts/quality/run_unittests.py",
        ],
        artifact="runtime/test_output.txt",
    )
    run_step(
        root,
        "Coverage report",
        [python, "-m", "coverage", "report"],
        artifact="runtime/coverage.txt",
    )
    run_step(
        root,
        "Coverage JSON",
        [python, "-m", "coverage", "json", "-o", "runtime/coverage.json"],
    )
    coverage_command = [
        python,
        "operations/scripts/quality/check_coverage.py",
        "--coverage-json",
        "runtime/coverage.json",
    ]
    if base:
        coverage_command.extend(["--base", base])
    else:
        coverage_command.append("--skip-diff")
    run_step(root, "Coverage policy", coverage_command, artifact="runtime/coverage_policy.txt")
    run_step(
        root,
        "Generated drift",
        ["git", "diff", "--exit-code", "--", "project_status.md", "tasks.md", "generated"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Canonical repository quality suite")
    parser.add_argument("profile", choices=("fast", "full"))
    parser.add_argument("--coverage-base", help="Git revision used for changed-line coverage")
    args = parser.parse_args()
    root = find_project_root(Path.cwd())
    try:
        if args.profile == "fast":
            run_fast(root, sys.executable)
        else:
            run_full(root, sys.executable, args.coverage_base)
    except QualityFailure as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"\nQuality suite ({args.profile}) passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
