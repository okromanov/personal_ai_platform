from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
from datetime import date
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import find_project_root
from operations.scripts.quality.scope import PYTHON_QUALITY_PATHS, PYTHON_SOURCE_PATHS


class QualityFailure(RuntimeError):
    pass


IGNORED_CONFIG_DIRS = {".git", ".venv", "node_modules", "runtime"}
EXACT_REQUIREMENT = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)==(?P<version>[A-Za-z0-9][A-Za-z0-9._+!-]*)$"
)
DEV_REQUIREMENTS_PATH = Path("operations/quality/requirements_dev.txt")
DEV_REQUIREMENTS_INPUT_PATH = Path("operations/quality/requirements_dev.in")
DEFAULT_STEP_TIMEOUT_SECONDS = 300
AUDIT_BASELINE_DIRECTORY = Path("work/audit")
AUDIT_REGISTER_PATH = AUDIT_BASELINE_DIRECTORY / "audit_register.md"
AUDIT_ROW = re.compile(
    r"^\|\s*(?:\[(?P<linked_id>AUD-\d{3})\]\([^)]+\)|(?P<bare_id>AUD-\d{3}))\s*\|\s*"
    r"(?P<severity>critical|high|medium|low)\s*\|\s*"
    r"(?P<state>open|remediated_pending_verification|resolved|accepted_risk)\s*\|\s*"
    r"(?P<first_seen>\d{4}-\d{2}-\d{2})\s*\|\s*"
    r"(?P<review_date>\d{4}-\d{2}-\d{2}|—)\s*\|\s*(?P<owner>[^|]+?)\s*\|"
)
# Function parameters Vulture flags as unused (100% confidence) but that are
# kept intentionally: evidence_ref/semantic_review_ref preserve caller
# clarity in acceptance/apply.py's apply_acceptance() even though only their
# digests are persisted (local file paths aren't reproducible across
# machines); arch_count mirrors sibling generator signatures in
# requirements/requirement_wizard.py's generate_task_documents(), which
# iterates context.arch_components directly instead.
VULTURE_IGNORED_NAMES = "evidence_ref,semantic_review_ref,arch_count"

# Оба профиля сторожат одни и те же производные пути. Пока списки жили
# врозь, `fast` проверял на дрейф ещё и `generated`, а `full` — нет: более
# полный профиль давал более слабую гарантию, чем более быстрый.
GENERATED_DRIFT_PATHS = ("project_status.md", "generated")


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
    input_path = root / DEV_REQUIREMENTS_INPUT_PATH
    lock_path = root / DEV_REQUIREMENTS_PATH
    for path in (input_path, lock_path):
        if not path.is_file():
            raise QualityFailure(f"Missing {path.relative_to(root).as_posix()}")

    direct_packages: dict[str, tuple[str, int]] = {}
    for line_number, raw_line in enumerate(
        input_path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = EXACT_REQUIREMENT.fullmatch(line)
        if match is None:
            raise QualityFailure(
                f"{DEV_REQUIREMENTS_INPUT_PATH.as_posix()}:{line_number}: "
                "dependency must use exact name==version pin"
            )
        normalized = re.sub(r"[-_.]+", "-", match.group("name")).lower()
        if normalized in direct_packages:
            raise QualityFailure(
                f"{DEV_REQUIREMENTS_INPUT_PATH.as_posix()}:{line_number}: duplicate dependency "
                f"{match.group('name')} (first declared on line "
                f"{direct_packages[normalized][1]})"
            )
        direct_packages[normalized] = (match.group("version"), line_number)
    if not direct_packages:
        raise QualityFailure(
            f"{DEV_REQUIREMENTS_INPUT_PATH.as_posix()} must contain at least one pinned dependency"
        )

    lock_text = lock_path.read_text(encoding="utf-8-sig")
    if "--index-url" in lock_text or "--extra-index-url" in lock_text:
        raise QualityFailure(f"{DEV_REQUIREMENTS_PATH.as_posix()} must not embed package indexes")
    locked_packages: dict[str, tuple[str, int, int]] = {}
    current_name: str | None = None
    for line_number, raw_line in enumerate(lock_text.splitlines(), start=1):
        if raw_line and not raw_line[0].isspace() and not raw_line.startswith("#"):
            header = raw_line.removesuffix(" \\").strip()
            match = EXACT_REQUIREMENT.fullmatch(header)
            if match is None:
                raise QualityFailure(
                    f"{DEV_REQUIREMENTS_PATH.as_posix()}:{line_number}: invalid locked pin"
                )
            current_name = re.sub(r"[-_.]+", "-", match.group("name")).lower()
            if current_name in locked_packages:
                raise QualityFailure(
                    f"{DEV_REQUIREMENTS_PATH.as_posix()}:{line_number}: duplicate locked dependency"
                )
            locked_packages[current_name] = (match.group("version"), line_number, 0)
        elif "--hash=sha256:" in raw_line and current_name is not None:
            version, header_line, hash_count = locked_packages[current_name]
            locked_packages[current_name] = (version, header_line, hash_count + 1)

    if not locked_packages:
        raise QualityFailure(f"{DEV_REQUIREMENTS_PATH.as_posix()} contains no locked dependencies")
    unhashed = sorted(name for name, (_, _, hashes) in locked_packages.items() if hashes == 0)
    if unhashed:
        raise QualityFailure(
            f"{DEV_REQUIREMENTS_PATH.as_posix()} dependencies without SHA-256 hashes: "
            + ", ".join(unhashed)
        )
    for name, (version, _) in direct_packages.items():
        locked = locked_packages.get(name)
        if locked is None or locked[0] != version:
            raise QualityFailure(
                f"{DEV_REQUIREMENTS_PATH.as_posix()} is stale for direct dependency "
                f"{name}=={version}"
            )


def validate_configuration_files(root: Path) -> None:
    validate_json_files(root)
    validate_toml_files(root)
    validate_development_requirements(root)
    validate_audit_baseline(root)


def validate_audit_baseline(root: Path, *, today: date | None = None) -> None:
    path = root / AUDIT_REGISTER_PATH
    if not path.is_file():
        raise QualityFailure(f"Missing audit register at {AUDIT_REGISTER_PATH.as_posix()}")
    relative_path = path.relative_to(root).as_posix()
    records: dict[str, tuple[str, str, str, str]] = {}
    current_date = today or date.today()
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not re.match(r"^\|\s*(?:\[)?AUD-\d{3}", line):
            continue
        match = AUDIT_ROW.match(line)
        if match is None:
            raise QualityFailure(f"{relative_path}:{line_number}: invalid audit record")
        finding_id = match.group("linked_id") or match.group("bare_id")
        severity = match.group("severity")
        state = match.group("state")
        review_date = match.group("review_date")
        owner = match.group("owner")
        if finding_id in records:
            raise QualityFailure(f"{relative_path}:{line_number}: duplicate {finding_id}")
        owner = owner.strip().strip("`")
        if state != "resolved" and (owner in {"", "none", "—"} or review_date == "—"):
            raise QualityFailure(
                f"{relative_path}:{line_number}: {finding_id} requires owner and review date"
            )
        if state != "resolved" and review_date != "—":
            try:
                parsed_review_date = date.fromisoformat(review_date)
            except ValueError as exc:
                raise QualityFailure(
                    f"{relative_path}:{line_number}: {finding_id} has invalid review date"
                ) from exc
            if parsed_review_date < current_date:
                raise QualityFailure(
                    f"{relative_path}:{line_number}: {finding_id} review date "
                    f"{review_date} is overdue as of {current_date.isoformat()}"
                )
        records[finding_id] = (severity, state, owner, review_date)
    if not records:
        raise QualityFailure(f"{relative_path} contains no AUD records")

    # `resolved` (§2/§5 of the register) requires a green canonical gate on
    # the exact SHA. A critical finding still `open` is itself proof that
    # gate has not run end to end (that is the entire point of severity
    # `critical`) -- so no other row can honestly be `resolved` at the same
    # time. This is the systemic guard for the AUD-029/030 drift: two
    # duplicate-baseline rows were hand-marked `resolved` while a critical
    # open finding (CI not dispatching) made that impossible to verify.
    critical_open = sorted(
        finding_id
        for finding_id, (severity, state, _, _) in records.items()
        if severity == "critical" and state == "open"
    )
    if critical_open:
        resolved = sorted(
            finding_id for finding_id, (_, state, _, _) in records.items() if state == "resolved"
        )
        if resolved:
            raise QualityFailure(
                f"{relative_path}: {', '.join(resolved)} marked resolved while critical "
                f"open finding(s) {', '.join(critical_open)} remain -- resolved requires a "
                "green canonical gate on the exact SHA, which cannot be claimed while a "
                "critical finding is still open"
            )


def validate_python_permissions(root: Path) -> None:
    if os.name == "nt":
        return
    executable = [
        path.relative_to(root).as_posix()
        for relative in PYTHON_QUALITY_PATHS
        for base in (root / relative,)
        for path in base.rglob("*.py")
        if path.stat().st_mode & 0o111
    ]
    if executable:
        raise QualityFailure("Python files must not be executable: " + ", ".join(executable))


def run_step(
    root: Path,
    name: str,
    command: list[str],
    *,
    artifact: str | None = None,
    timeout_seconds: int = DEFAULT_STEP_TIMEOUT_SECONDS,
) -> None:
    print(f"\n== {name} ==")
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        if output:
            print(output, end="" if output.endswith("\n") else "\n")
        if artifact:
            target = root / artifact
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                output or f"{name}: timed out after {timeout_seconds} seconds\n",
                encoding="utf-8",
            )
        raise QualityFailure(f"{name} timed out after {timeout_seconds} seconds") from exc
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
        [python, "-m", "compileall", "-q", *PYTHON_QUALITY_PATHS],
    )
    run_step(
        root, "Fast repository checks", [python, "operations/scripts/documents/check.py", "--fast"]
    )
    run_step(
        root,
        "Ruff lint",
        [python, "-m", "ruff", "check", *PYTHON_QUALITY_PATHS],
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
        ["git", "diff", "--exit-code", "--", *GENERATED_DRIFT_PATHS],
    )


def run_full(root: Path, python: str, base: str | None) -> None:
    validate_configuration_files(root)
    validate_python_permissions(root)
    (root / "runtime").mkdir(exist_ok=True)
    if base:
        run_step(
            root,
            "Change scope and immutable audit history",
            [
                python,
                "operations/scripts/tasks/check_change_scope.py",
                "--base",
                base,
                "--head",
                "HEAD",
            ],
        )
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
            *PYTHON_SOURCE_PATHS,
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
            *PYTHON_QUALITY_PATHS,
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
            *PYTHON_QUALITY_PATHS,
            "--output-format",
            "concise",
        ],
        artifact="runtime/ruff_check.txt",
    )
    run_step(
        root,
        "Ruff format",
        [python, "-m", "ruff", "format", *PYTHON_QUALITY_PATHS, "--check"],
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
        "Template registry",
        [python, "operations/scripts/documents/template_contracts.py"],
    )
    run_step(
        root,
        "Generated drift",
        ["git", "diff", "--exit-code", "--", *GENERATED_DRIFT_PATHS],
    )
    run_step(
        root,
        "Repository health check",
        [
            python,
            "operations/scripts/health_check/generate.py",
            "--output",
            "runtime/health_check_report.md",
            "--json",
            "runtime/health_check.json",
        ],
        artifact="runtime/health_check_output.txt",
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
