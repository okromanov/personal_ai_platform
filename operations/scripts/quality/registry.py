from __future__ import annotations

import fnmatch
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict, cast

REGISTRY_PATH = "operations/quality_registry.json"
COVERAGE_MODES = {"task_test", "global_evidence"}
DERIVED_PATH_PATTERNS = (
    "generated/**",
    "runtime/**",
    "project_status.md",
    "tasks.md",
    "owner_dashboard.md",
    "work/m*_final_report.md",
)
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
RUN_URL_PATTERN = re.compile(r"^https://github\.com/[^/]+/[^/]+/actions/runs/\d+$")
RECORD_TYPES = {"quality_suite", "test_evidence"}


class QualityProfile(TypedDict):
    """Coerced, typed view of a `profiles.<id>` entry from quality_registry.json.

    The raw JSON value is `object`-typed by construction (parsed at runtime,
    validated separately by `validate_quality_registry`). Parsing it once into
    this shape here means every consumer works with real list[str]/str fields
    instead of re-deriving them from `object` at each call site.
    """

    milestones: list[str]
    required_evidence: list[str]
    paths: list[str]
    scope_coverage: str
    scope_evidence: list[str]


def _parse_profile(raw: dict[str, object]) -> QualityProfile:
    milestones = raw.get("milestones", [])
    required = raw.get("required_evidence", [])
    paths = raw.get("paths", [])
    scope_evidence = raw.get("scope_evidence", [])
    return {
        "milestones": [str(value) for value in milestones] if isinstance(milestones, list) else [],
        "required_evidence": (
            [str(value) for value in required] if isinstance(required, list) else []
        ),
        "paths": [str(value) for value in paths] if isinstance(paths, list) else [],
        "scope_coverage": str(raw.get("scope_coverage", "task_test")),
        "scope_evidence": (
            [str(value) for value in scope_evidence] if isinstance(scope_evidence, list) else []
        ),
    }


def validate_server_source(
    raw: object,
    *,
    expected_sha: str | None = None,
    require_artifact: bool = False,
) -> list[str]:
    """Validate immutable GitHub Actions provenance carried by evidence."""
    if not isinstance(raw, dict):
        return ["server_source должен быть object"]
    errors: list[str] = []
    required = {"repository", "workflow", "run_id", "run_url", "event_sha"}
    if require_artifact:
        required.update({"artifact_id", "artifact_digest"})
    missing = sorted(key for key in required if not str(raw.get(key, "")).strip())
    if missing:
        errors.append("server_source не содержит: " + ", ".join(missing))
        return errors
    event_sha = str(raw.get("event_sha", "")).lower()
    if not SHA_PATTERN.fullmatch(event_sha):
        errors.append("server_source.event_sha должен быть 40-символьным SHA")
    elif expected_sha and event_sha != expected_sha.lower():
        errors.append(
            f"server_source.event_sha={event_sha} не совпадает с ожидаемым SHA {expected_sha}"
        )
    if not str(raw.get("run_id", "")).isdigit():
        errors.append("server_source.run_id должен быть числовым")
    if not RUN_URL_PATTERN.fullmatch(str(raw.get("run_url", ""))):
        errors.append("server_source.run_url должен ссылаться на GitHub Actions run")
    if require_artifact:
        if not str(raw.get("artifact_id", "")).isdigit():
            errors.append("server_source.artifact_id должен быть числовым")
        digest = str(raw.get("artifact_digest", "")).lower()
        if digest.startswith("sha256:"):
            digest = digest.removeprefix("sha256:")
        if not SHA256_PATTERN.fullmatch(digest):
            errors.append("server_source.artifact_digest должен быть SHA-256")
    return errors


def validate_evidence_record(
    raw: object,
    *,
    evidence_id: str,
    expected_type: str,
    expected_sha: str | None = None,
) -> list[str]:
    """Validate a record before its result can influence a quality gate."""
    if not isinstance(raw, dict):
        return ["record должен быть JSON object"]
    errors: list[str] = []
    if expected_type not in RECORD_TYPES or str(raw.get("type", "")) != expected_type:
        errors.append(f"type должен быть {expected_type}")
    if expected_type == "test_evidence" and str(raw.get("evidence_id", "")) != evidence_id:
        errors.append(f"evidence_id должен быть {evidence_id}")
    if str(raw.get("result", "")).lower() not in {"passed", "failed", "blocked"}:
        errors.append("result должен быть passed, failed или blocked")
    git_sha = str(raw.get("git_sha", "")).lower()
    if not SHA_PATTERN.fullmatch(git_sha):
        errors.append("git_sha должен быть 40-символьным SHA")
    elif expected_sha and git_sha != expected_sha.lower():
        errors.append(f"git_sha={git_sha} не совпадает с текущим SHA {expected_sha}")
    if not str(raw.get("checked_at", "")).strip():
        errors.append("checked_at отсутствует")
    if not isinstance(raw.get("environment"), dict) or not raw.get("environment"):
        errors.append("environment должен быть непустым object")
    command = raw.get("command")
    if (
        not isinstance(command, list)
        or not command
        or any(not isinstance(value, str) or not value.strip() for value in command)
    ):
        errors.append("command должен быть непустым list строк")
    exit_code = raw.get("exit_code")
    if not isinstance(exit_code, int) or isinstance(exit_code, bool):
        errors.append("exit_code должен быть integer")
    elif str(raw.get("result", "")).lower() == "passed" and exit_code != 0:
        errors.append("passed несовместим с ненулевым exit_code")
    artifacts = raw.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("artifacts должен быть непустым list")
    else:
        for index, artifact in enumerate(artifacts, start=1):
            if not isinstance(artifact, dict):
                errors.append(f"artifact {index} должен быть object")
                continue
            if (
                not str(artifact.get("path", "")).strip()
                or not isinstance(artifact.get("bytes"), int)
                or int(artifact.get("bytes", 0)) <= 0
                or not SHA256_PATTERN.fullmatch(str(artifact.get("sha256", "")).lower())
            ):
                errors.append(f"artifact {index} требует path, положительный bytes и sha256")
    errors.extend(
        f"server_source: {message}"
        for message in validate_server_source(
            raw.get("server_source"),
            expected_sha=git_sha if SHA_PATTERN.fullmatch(git_sha) else expected_sha,
        )
    )
    return errors


def load_quality_registry(root: Path) -> dict[str, object]:
    path = root / REGISTRY_PATH
    if not path.is_file():
        raise ValueError(f"Отсутствует {REGISTRY_PATH}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("quality registry должен быть JSON object")
    return data


def validate_quality_registry(root: Path, milestone_ids: set[str]) -> list[str]:
    errors: list[str] = []
    try:
        registry = load_quality_registry(root)
    except Exception as exc:
        return [str(exc)]
    catalog = registry.get("evidence_catalog")
    profiles = registry.get("profiles")
    if not isinstance(catalog, dict) or not catalog:
        errors.append("quality registry: evidence_catalog отсутствует или пуст")
        catalog = {}
    if not isinstance(profiles, dict) or not profiles:
        errors.append("quality registry: profiles отсутствует или пуст")
        profiles = {}

    for evidence_id, raw in catalog.items():
        if not isinstance(raw, dict):
            errors.append(f"evidence {evidence_id}: ожидается object")
            continue
        if str(raw.get("class", "hard")) not in {"hard", "advisory"}:
            errors.append(f"evidence {evidence_id}: class должен быть hard или advisory")
        if not str(raw.get("source", "")).strip():
            errors.append(f"evidence {evidence_id}: отсутствует source")
        source = str(raw.get("source", "")).strip()
        if source.startswith("record:"):
            record_type = str(raw.get("record_type", "")).strip()
            if record_type not in RECORD_TYPES:
                errors.append(
                    f"evidence {evidence_id}: record_type должен быть quality_suite или test_evidence"
                )
            relative = source.split(":", 1)[1].strip().replace("\\", "/")
            if not relative or relative.startswith("/") or ".." in Path(relative).parts:
                errors.append(f"evidence {evidence_id}: некорректный путь record")

    for profile_id, raw in profiles.items():
        if not isinstance(raw, dict):
            errors.append(f"quality profile {profile_id}: ожидается object")
            continue
        milestones = raw.get("milestones", [])
        required = raw.get("required_evidence", [])
        paths = raw.get("paths", [])
        coverage = str(raw.get("scope_coverage", "task_test"))
        scope_evidence = raw.get("scope_evidence", [])

        if not isinstance(milestones, list) or not milestones:
            errors.append(f"quality profile {profile_id}: milestones должен быть непустым list")
            milestones = []
        if not isinstance(required, list) or not required:
            errors.append(
                f"quality profile {profile_id}: required_evidence должен быть непустым list"
            )
            required = []
        if (
            not isinstance(paths, list)
            or not paths
            or any(not str(value).strip() for value in paths)
        ):
            errors.append(f"quality profile {profile_id}: paths должен быть непустым list шаблонов")
        if coverage not in COVERAGE_MODES:
            errors.append(f"quality profile {profile_id}: неизвестный scope_coverage '{coverage}'")
        if coverage == "global_evidence" and (
            not isinstance(scope_evidence, list) or not scope_evidence
        ):
            errors.append(f"quality profile {profile_id}: global_evidence требует scope_evidence")
            scope_evidence = []

        for milestone in milestones:
            value = str(milestone).lower()
            if value not in milestone_ids:
                errors.append(f"quality profile {profile_id}: неизвестный milestone {milestone}")
        for evidence in [*required, *(scope_evidence if isinstance(scope_evidence, list) else [])]:
            if str(evidence) not in catalog:
                errors.append(f"quality profile {profile_id}: неизвестный evidence {evidence}")
    return errors


def profiles_for_milestone(
    registry: dict[str, object], milestone_id: str
) -> list[tuple[str, QualityProfile]]:
    profiles = registry.get("profiles", {})
    result: list[tuple[str, QualityProfile]] = []
    if not isinstance(profiles, dict):
        return result
    for profile_id, raw in profiles.items():
        if not isinstance(raw, dict):
            continue
        profile = _parse_profile(raw)
        if milestone_id.lower() in [value.lower() for value in profile["milestones"]]:
            result.append((str(profile_id), profile))
    return result


def _normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.lstrip("/")


def _matches(path: str, patterns: list[str]) -> bool:
    # fnmatchcase, а не fnmatch: fnmatch применяет os.path.normcase и на Windows
    # становится регистронезависимым. Один и тот же путь не может считаться
    # покрытым на Windows и непокрытым на Linux — обе проверки обязаны совпадать.
    normalized = _normalize_path(path)
    return any(fnmatch.fnmatchcase(normalized, _normalize_path(pattern)) for pattern in patterns)


def impacted_profiles(registry: dict[str, object], changed_paths: list[str]) -> list[str]:
    result: list[str] = []
    profiles = registry.get("profiles", {})
    if not isinstance(profiles, dict):
        return result
    for profile_id, raw in profiles.items():
        if not isinstance(raw, dict):
            continue
        patterns = _parse_profile(raw)["paths"]
        if any(_matches(path, patterns) for path in changed_paths):
            result.append(str(profile_id))
    return result


def uncovered_paths(
    selected_profiles: list[tuple[str, QualityProfile]], changed_paths: list[str]
) -> list[str]:
    patterns: list[str] = []
    for _, profile in selected_profiles:
        patterns.extend(profile["paths"])
    result: list[str] = []
    for path in changed_paths:
        normalized = _normalize_path(path)
        if _matches(normalized, list(DERIVED_PATH_PATTERNS)):
            continue
        if not patterns or not _matches(normalized, patterns):
            result.append(normalized)
    return sorted(dict.fromkeys(result))


def evidence_results(
    registry: dict[str, object],
    *,
    root: Path | None = None,
    check_summary: Mapping[str, object],
    unit_summary: Mapping[str, object],
    context: Mapping[str, object] | None = None,
) -> dict[str, dict[str, object]]:
    # check_summary is external input (parsed from check.py's JSON output), not
    # typed beyond Mapping[str, object].
    raw_checks = cast(list[object], check_summary.get("checks", []))
    checks = {
        str(item.get("name")): bool(item.get("ok")) for item in raw_checks if isinstance(item, dict)
    }
    context = context or {}
    results: dict[str, dict[str, object]] = {}
    catalog = registry.get("evidence_catalog", {})
    if not isinstance(catalog, dict):
        return results
    for evidence_id, raw in catalog.items():
        item = raw if isinstance(raw, dict) else {}
        source = str(item.get("source", "future"))
        record_data: dict[str, object] = {}
        validation_errors: list[str] = []
        value: bool | None
        if source == "checker":
            value = bool(check_summary.get("ok"))
        elif source == "unit_tests":
            value = bool(unit_summary.get("ok"))
        elif source.startswith("check:"):
            name = source.split(":", 1)[1]
            value = checks.get(name)
        elif source.startswith("record:"):
            record_path = source.split(":", 1)[1].strip()
            value = None
            if root is not None and record_path:
                candidate = (root / record_path).resolve()
                try:
                    candidate.relative_to(root.resolve())
                except ValueError:
                    candidate = root / "__invalid_evidence_path__"
                if candidate.is_file():
                    try:
                        record = json.loads(candidate.read_text(encoding="utf-8"))
                        record_data = record if isinstance(record, dict) else {}
                        catalog_type = str(item.get("record_type", ""))
                        expected_sha = str(context.get("git_sha", "")).lower()
                        validation_errors = validate_evidence_record(
                            record_data,
                            evidence_id=str(evidence_id),
                            expected_type=catalog_type,
                            expected_sha=expected_sha
                            if SHA_PATTERN.fullmatch(expected_sha)
                            else None,
                        )
                        recorded_result = str(record_data.get("result", "missing")).lower()
                        value = (
                            None
                            if validation_errors
                            else True
                            if recorded_result == "passed"
                            else False
                        )
                    except (OSError, ValueError, TypeError):
                        value = None
        else:
            value = None
        results[str(evidence_id)] = {
            "result": "passed" if value is True else "failed" if value is False else "missing",
            "class": str(item.get("class", "hard")),
            "source": source,
            "git_sha": str(record_data.get("git_sha", context.get("git_sha", "unknown"))),
            "timestamp": str(record_data.get("checked_at", context.get("timestamp", "unknown"))),
            "environment": record_data.get("environment", context.get("environment", {})),
            "server_source": record_data.get("server_source"),
            "type": record_data.get("type"),
            "evidence_id": record_data.get("evidence_id"),
            "command": record_data.get("command"),
            "exit_code": record_data.get("exit_code"),
            "artifacts": record_data.get("artifacts"),
            "validation_errors": validation_errors if source.startswith("record:") else [],
        }
    return results


class MilestoneQualityResult(TypedDict):
    profiles: list[str]
    evidence: list[dict[str, object]]
    blockers: list[str]
    warnings: list[str]
    ready: bool


def evaluate_milestone_quality(
    root: Path,
    milestone_id: str,
    *,
    check_summary: Mapping[str, object],
    unit_summary: Mapping[str, object],
    context: Mapping[str, object] | None = None,
) -> MilestoneQualityResult:
    registry = load_quality_registry(root)
    results = evidence_results(
        registry,
        root=root,
        check_summary=check_summary,
        unit_summary=unit_summary,
        context=context,
    )
    selected_profiles = profiles_for_milestone(registry, milestone_id)
    selected = [profile_id for profile_id, _ in selected_profiles]
    required: list[str] = []
    for _, profile in selected_profiles:
        for value in profile["required_evidence"]:
            if value and value not in required:
                required.append(value)

    blockers: list[str] = []
    warnings: list[str] = []
    if not selected:
        blockers.append(f"quality profile missing for {milestone_id.lower()}")
    rows: list[dict[str, object]] = []
    for evidence_id in required:
        result = results.get(
            evidence_id, {"result": "missing", "class": "hard", "source": "unknown"}
        )
        raw_validation_errors = result.get("validation_errors", [])
        row = {
            "id": evidence_id,
            "result": str(result["result"]),
            "class": str(result["class"]),
            "source": str(result["source"]),
            "git_sha": str(result.get("git_sha", "unknown")),
            "timestamp": str(result.get("timestamp", "unknown")),
            "environment": result.get("environment", {}),
            "server_source": result.get("server_source"),
            "type": result.get("type"),
            "evidence_id": result.get("evidence_id"),
            "command": result.get("command"),
            "exit_code": result.get("exit_code"),
            "artifacts": result.get("artifacts"),
            "validation_errors": (
                list(raw_validation_errors) if isinstance(raw_validation_errors, list) else []
            ),
        }
        rows.append(row)
        if row["result"] != "passed":
            message = f"{evidence_id}: {row['result']} ({row['source']})"
            if row["class"] == "hard":
                blockers.append(message)
            else:
                warnings.append(message)
    return {
        "profiles": selected,
        "evidence": rows,
        "blockers": blockers,
        "warnings": warnings,
        "ready": not blockers,
    }
