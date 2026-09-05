from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import SupportsInt, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import (
    atomic_write,
    find_project_root,
    now_iso_minutes,
    read_text,
    relative_posix,
    require_supported_python,
    run_command,
)
from operations.scripts.documents.metadata import load_document, metadata_list
from operations.scripts.quality.registry import (
    validate_evidence_record,
    validate_server_source,
)
from operations.scripts.status.generate_project_status import _change_scope

MILESTONE_HEADING = re.compile(r"^##\s+(m\d{2})\s+—\s+.+?$", re.MULTILINE | re.IGNORECASE)
MILESTONE_WORK_STATE = re.compile(r"(?m)^-\s+work_state:\s+`?([a-z-]+)`?\s*$", re.IGNORECASE)
V1_SCOPE_LINE = re.compile(r"(?m)^Обязательный состав продукта:\s*(.+?)\s*$")
SEMANTIC_SCORE_KEYS = {
    "clarity",
    "consistency",
    "hierarchy",
    "automation",
    "owner_usability",
    "agent_readiness",
    "language",
    "minimality",
    "overall",
}
SEMANTIC_SEVERITIES = {"critical", "high", "medium", "low"}
M01_STRATEGIC_ANSWER_KEYS = {
    "v1_scope",
    "m02_interfaces",
    "portability_boundary",
    "scheduled_tasks_order",
    "model_outage_strategy",
}


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_confirmation(milestone_id: str) -> str:
    return f"ПРИНИМАЮ {milestone_id.lower()}"


def canonical_v1_scope_ids(root: Path) -> list[str]:
    text = read_text(root / "milestones.md")
    match = V1_SCOPE_LINE.search(text)
    if match:
        # Explicit list found
        identifiers = re.findall(r"\bBR_\d{3}\b", match.group(1))
        if not identifiers:
            raise ValueError("Канонический обязательный состав V1 пуст")
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Канонический обязательный состав V1 содержит повторные ID")
        return identifiers
    else:
        # No explicit list: derive from core-priority requirements
        br_text = read_text(root / "specifications" / "business_requirements.md")
        br_pattern = re.compile(r"(?ms)^###\s+(BR_\d{3})\s+—.*?^-\s+priority:\s*`([a-z]+)`\s*$")
        core_brs = sorted(
            [match.group(1) for match in br_pattern.finditer(br_text) if match.group(2) == "core"]
        )
        if not core_brs:
            raise ValueError("Не найдено ни одного BR с приоритетом `core`")
        return core_brs


def validate_confirmation(milestone_id: str, confirmation: str) -> None:
    expected = expected_confirmation(milestone_id)
    if confirmation.strip() != expected:
        raise ValueError(f"Неверное подтверждение. Ожидается точная строка: {expected}")


def _replace_front_matter_state(
    text: str,
    *,
    field: str,
    allowed_from: set[str],
    target: str,
    updated: str | None = None,
) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.startswith("---\n"):
        raise ValueError("Документ не содержит front matter")
    end = normalized.find("\n---\n", 4)
    if end == -1:
        raise ValueError("Некорректный front matter")
    head = normalized[: end + 5]
    body = normalized[end + 5 :]
    match = re.search(rf"(?m)^{re.escape(field)}:\s*([^\n]+)\s*$", head)
    if not match:
        raise ValueError(f"Front matter не содержит {field}")
    current = match.group(1).strip().strip("\"'").lower()
    if current == target:
        return normalized
    if current not in allowed_from:
        raise ValueError(f"Недопустимый переход {field}: {current} → {target}")
    head = head[: match.start(1)] + target + head[match.end(1) :]
    if updated:
        updated_match = re.search(r"(?m)^updated:\s*([^\n]+)\s*$", head)
        if not updated_match:
            raise ValueError("Front matter не содержит updated")
        head = head[: updated_match.start(1)] + updated + head[updated_match.end(1) :]
    return head + body


def _replace_front_matter_updated(text: str, updated: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.startswith("---\n"):
        raise ValueError("Документ не содержит front matter")
    end = normalized.find("\n---\n", 4)
    if end == -1:
        raise ValueError("Некорректный front matter")
    head = normalized[: end + 5]
    body = normalized[end + 5 :]
    match = re.search(r"(?m)^updated:\s*([^\n]+)\s*$", head)
    if not match:
        raise ValueError("Front matter не содержит updated")
    return head[: match.start(1)] + updated + head[match.end(1) :] + body


def _replace_milestone_work_state(text: str, milestone_id: str, target: str = "completed") -> str:
    matches = list(MILESTONE_HEADING.finditer(text))
    for index, match in enumerate(matches):
        if match.group(1).lower() != milestone_id.lower():
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.end() : end]
        state = MILESTONE_WORK_STATE.search(section)
        if not state:
            raise ValueError(f"{milestone_id}: отсутствует work_state")
        current = state.group(1).lower()
        if current == target:
            return text
        if current != "in-progress":
            raise ValueError(
                f"{milestone_id}: недопустимый переход work_state {current} → {target}"
            )
        absolute_start = match.end() + state.start(1)
        absolute_end = match.end() + state.end(1)
        return text[:absolute_start] + target + text[absolute_end:]
    raise ValueError(f"Не найден milestone {milestone_id}")


def _git_head(root: Path) -> str:
    result = run_command(["git", "rev-parse", "HEAD"], cwd=root)
    if not result.ok:
        raise ValueError("Не удалось определить Git HEAD")
    return result.stdout.strip()


def _commit_authors(root: Path, sha: str) -> set[str]:
    """Авторы коммитов, приведших к проверяемому SHA (до 200 последних)."""
    result = run_command(["git", "log", "--format=%ae%n%an", "-n", "200", sha], cwd=root)
    if not result.ok:
        return set()
    return {line.strip().lower() for line in result.stdout.splitlines() if line.strip()}


def validate_reviewer_independence(root: Path, data: dict[str, object], sha: str) -> None:
    """Сверить заявленную независимость проверки с авторством коммитов.

    `review_context: fresh-session` подтверждается только тем, что кто-то это
    написал. Здесь декларация связывается с наблюдаемым фактом: проверяющий не
    должен входить в число авторов проверяемого диапазона.

    В проекте одного владельца это условие невыполнимо — он и автор изменений,
    и единственный проверяющий. Поэтому предусмотрен явный режим
    `reviewer_is_author_acknowledged`, который не выдаёт совпадение за
    независимость, а фиксирует его в записи. Запрещено именно молчаливое
    совпадение: контроль, который можно обойти не заметив, контролем не является.
    """
    reviewer = str(data.get("reviewer", "")).strip().lower()
    if not reviewer:
        return
    authors = _commit_authors(root, sha)
    if reviewer not in authors:
        return
    if data.get("reviewer_is_author_acknowledged") is True:
        return
    raise ValueError(
        f"Semantic review: reviewer '{reviewer}' входит в число авторов проверяемого "
        "диапазона, а review_context заявляет независимость. Либо проверку выполняет "
        "кто-то другой, либо запись обязана содержать "
        "reviewer_is_author_acknowledged: true"
    )


def _git_branch(root: Path) -> str:
    result = run_command(["git", "branch", "--show-current"], cwd=root)
    if not result.ok:
        raise ValueError("Не удалось определить Git branch")
    return result.stdout.strip()


def _require_clean_worktree(root: Path) -> None:
    """Доказательство обязано отражать закоммиченный SHA, а не рабочее дерево.

    Без этой проверки evidence bundle можно было собрать поверх незакоммиченных
    правок: git_sha совпадёт с HEAD, но фактически проверенное содержимое
    останется незафиксированным и способно разойтись с тем, что попадёт в PR.
    """
    result = run_command(["git", "status", "--porcelain"], cwd=root)
    if not result.ok:
        raise ValueError("Не удалось проверить чистоту рабочего дерева")
    if result.stdout.strip():
        raise ValueError(
            "Рабочее дерево содержит незакоммиченные изменения: evidence должен "
            "быть собран на чистом закоммиченном SHA"
        )


def validate_evidence_bundle(root: Path, path: Path, milestone_id: str) -> dict[str, object]:
    _require_clean_worktree(root)
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError as e:
        raise ValueError(f"Evidence file is not valid JSON: {e}")
    if not isinstance(data, dict):
        raise ValueError("Evidence bundle должен быть JSON object")
    if data.get("schema_version") != 2:
        raise ValueError("Evidence bundle должен иметь schema_version=2")
    if str(data.get("milestone", "")).lower() != milestone_id.lower():
        raise ValueError("Evidence bundle относится к другому milestone")
    state = str(data.get("acceptance_state", ""))
    if state != "ready-for-semantic-review":
        raise ValueError("Evidence bundle не подтверждает применимую техническую готовность")
    pending = {str(value) for value in data.get("pending_gates", [])}
    if pending != {"semantic_review"}:
        raise ValueError(
            f"{milestone_id}: evidence должен иметь единственный pending gate semantic_review"
        )
    if data.get("blockers", []):
        raise ValueError("Evidence bundle содержит blockers")
    expected_sha = str(data.get("git_sha", ""))
    actual_sha = _git_head(root)
    if not expected_sha or expected_sha != actual_sha:
        raise ValueError(
            f"Evidence SHA mismatch: evidence={expected_sha or 'missing'}, HEAD={actual_sha}"
        )
    provenance_errors = validate_server_source(data.get("server_source"), expected_sha=actual_sha)
    if provenance_errors:
        raise ValueError(
            "Evidence bundle не подтверждает серверное происхождение: "
            + "; ".join(provenance_errors)
        )
    rows = data.get("evidence")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Evidence bundle не содержит обязательные evidence rows")
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Evidence row {index} должен быть object")
        evidence_id = str(row.get("id", f"row-{index}"))
        if str(row.get("result", "")) != "passed":
            raise ValueError(f"Evidence {evidence_id} не имеет result=passed")
        if str(row.get("git_sha", "")).lower() != actual_sha.lower():
            raise ValueError(f"Evidence {evidence_id} относится к другому Git SHA")
        if (
            not str(row.get("timestamp", "")).strip()
            or not isinstance(row.get("environment"), dict)
            or not row.get("environment")
        ):
            raise ValueError(f"Evidence {evidence_id} не содержит timestamp/environment")
        validation_errors = row.get("validation_errors", [])
        if not isinstance(validation_errors, list) or validation_errors:
            raise ValueError(f"Evidence {evidence_id} не прошло строгую проверку schema")
        if str(row.get("source", "")).startswith("record:"):
            expected_type = str(row.get("type", ""))
            record_source_errors = validate_evidence_record(
                row,
                evidence_id=evidence_id,
                expected_type=expected_type,
                expected_sha=actual_sha,
            )
            if record_source_errors:
                raise ValueError(
                    f"Evidence {evidence_id} не проходит строгую record schema: "
                    + "; ".join(record_source_errors)
                )
    if (
        not str(data.get("timestamp", "")).strip()
        or not isinstance(data.get("environment"), dict)
        or not data.get("environment")
    ):
        raise ValueError("Evidence bundle не содержит timestamp/environment")
    coverage = data.get("coverage", {})
    if isinstance(coverage, dict) and int(coverage.get("scope_covered", 0)) != int(
        coverage.get("scope_total", 0)
    ):
        raise ValueError("Evidence bundle не подтверждает полное milestone scope coverage")
    if isinstance(coverage, dict):
        raw_tracked_total = coverage.get("tracked_total")
        if raw_tracked_total is None:
            raw_tracked_total = coverage.get("scope_total", 0)
        raw_tracked_covered = coverage.get("tracked_covered")
        if raw_tracked_covered is None:
            raw_tracked_covered = coverage.get("scope_covered", 0)
        tracked_total = int(cast(SupportsInt, raw_tracked_total))
        tracked_covered = int(cast(SupportsInt, raw_tracked_covered))
        if tracked_covered != tracked_total:
            raise ValueError("Evidence bundle не подтверждает полное покрытие проверяемых областей")
        if milestone_id.lower() == "m01" and tracked_total <= 0:
            raise ValueError("Evidence bundle m01 не содержит проверяемых областей основы")
    if data.get("uncovered_paths", []):
        raise ValueError("Evidence bundle содержит пути вне профиля качества")

    recorded_base = data.get("coverage_base")
    if not isinstance(recorded_base, dict):
        raise ValueError("Evidence bundle не содержит основу полного покрытия")
    actual_scope = _change_scope(root, milestone_id)
    if actual_scope.get("error"):
        raise ValueError("Не удалось проверить основу покрытия: " + str(actual_scope["error"]))
    expected_base = {
        "mode": str(actual_scope.get("mode")),
        "git_sha": actual_scope.get("base_sha"),
    }
    if recorded_base != expected_base:
        raise ValueError(
            f"Evidence coverage base mismatch: evidence={recorded_base}, actual={expected_base}"
        )
    recorded_paths = {str(value) for value in data.get("changed_paths", [])}
    actual_paths = {str(value) for value in actual_scope.get("paths", [])}
    if recorded_paths != actual_paths:
        raise ValueError("Evidence bundle не содержит полную область путей текущего этапа")
    return data


def validate_semantic_review(root: Path, path: Path, milestone_id: str) -> dict[str, object]:
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError as e:
        raise ValueError(f"Semantic review file is not valid JSON: {e}")
    if not isinstance(data, dict):
        raise ValueError("Semantic review должен быть JSON object")
    if (
        str(data.get("type", "")) != "semantic_review"
        or str(data.get("milestone", "")).lower() != milestone_id.lower()
    ):
        raise ValueError("Semantic review имеет неверный type/milestone")
    if str(data.get("result", "")).lower() != "pass":
        raise ValueError("Semantic review не подтверждает PASS")
    actual_sha = _git_head(root)
    if str(data.get("reviewed_sha", "")) != actual_sha:
        raise ValueError("Semantic review SHA mismatch")
    if not str(data.get("timestamp", "")).strip() or not str(data.get("reviewer", "")).strip():
        raise ValueError("Semantic review не содержит timestamp/reviewer")
    if str(data.get("review_context", "")) not in {"fresh-session", "independent-reviewer"}:
        raise ValueError(
            "Semantic review должен быть выполнен в fresh-session или independent-reviewer"
        )
    validate_reviewer_independence(root, data, actual_sha)
    if data.get("lifecycle_tested") is not True:
        raise ValueError("Semantic review должен подтверждать полный lifecycle_tested")
    if milestone_id.lower() == "m01":
        scope_decision = str(data.get("v1_scope_owner_decision", "")).strip()
        if scope_decision != "ПОДТВЕРЖДАЮ СОСТАВ V1":
            raise ValueError(
                "Semantic review m01 не содержит явного подтверждения владельцем состава V1"
            )
        scope_ids = data.get("v1_scope_ids")
        expected_scope_ids = canonical_v1_scope_ids(root)
        if (
            not isinstance(scope_ids, list)
            or [str(value) for value in scope_ids] != expected_scope_ids
        ):
            raise ValueError("Semantic review m01 содержит неактуальный состав V1")
        strategic_answers = data.get("strategic_answers")
        if (
            not isinstance(strategic_answers, dict)
            or set(strategic_answers) != M01_STRATEGIC_ANSWER_KEYS
            or any(not str(value).strip() for value in strategic_answers.values())
        ):
            raise ValueError(
                "Semantic review m01 должен фиксировать ответы на пять стратегических вопросов"
            )
    artifacts = {str(value) for value in data.get("reviewed_artifacts", [])}
    required = {
        "AGENTS.md",
        "project_rules.md",
        "operations/change_process.md",
        "milestones.md",
        "project_status.md",
        "specifications/",
        "adr/",
        "operations/",
        "work/",
        ".github/workflows/",
    }
    missing = sorted(required - artifacts)
    if missing:
        raise ValueError(
            "Semantic review не покрывает обязательные artifacts: " + ", ".join(missing)
        )
    scores = data.get("scores")
    if not isinstance(scores, dict) or set(scores) != SEMANTIC_SCORE_KEYS:
        raise ValueError("Semantic review должен содержать полный набор scores")
    if any(
        not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 10
        for value in scores.values()
    ):
        raise ValueError("Semantic review scores должны быть числами от 0 до 10")
    findings = data.get("findings", [])
    if not isinstance(findings, list):
        raise ValueError("Semantic review findings должен быть list")
    unresolved_serious: list[str] = []
    for index, finding in enumerate(findings, start=1):
        if not isinstance(finding, dict):
            raise ValueError(f"Semantic review finding {index} должен быть object")
        severity = str(finding.get("severity", ""))
        state = str(finding.get("state", ""))
        if severity not in SEMANTIC_SEVERITIES or state not in {"unresolved", "resolved"}:
            raise ValueError(f"Semantic review finding {index} имеет неверные severity/state")
        if (
            not str(finding.get("evidence", "")).strip()
            or not str(finding.get("remediation", "")).strip()
        ):
            raise ValueError(f"Semantic review finding {index} не содержит evidence/remediation")
        locations = finding.get("locations")
        if not isinstance(locations, list) or not locations:
            raise ValueError(f"Semantic review finding {index} не содержит locations")
        for location_index, location in enumerate(locations, start=1):
            if not isinstance(location, dict):
                raise ValueError(
                    f"Semantic review finding {index}, location {location_index} должен быть object"
                )
            relative = str(location.get("path", "")).strip().replace("\\", "/")
            anchor = str(location.get("anchor", "")).strip()
            if (
                not relative
                or not anchor
                or relative.startswith("/")
                or ".." in Path(relative).parts
            ):
                raise ValueError(
                    f"Semantic review finding {index}, location {location_index} некорректен"
                )
            if not (root / relative).is_file():
                raise ValueError(
                    f"Semantic review finding {index} ссылается на отсутствующий файл {relative}"
                )
        if state == "unresolved" and severity in {"critical", "high"}:
            unresolved_serious.append(severity)
    if unresolved_serious:
        raise ValueError("Semantic review PASS содержит нерешённые critical/high замечания")
    if float(scores["overall"]) >= 9 and any(
        str(finding.get("severity")) in {"critical", "high"} for finding in findings
    ):
        raise ValueError("Semantic review overall >= 9 несовместим с critical/high замечаниями")
    return data


def _tasks_for_milestone(root: Path, milestone_id: str) -> list[tuple[Path, dict[str, object]]]:
    result: list[tuple[Path, dict[str, object]]] = []
    for path in sorted((root / "work/tasks").glob("task_*.md")):
        doc = load_document(path)
        if milestone_id.lower() in {
            value.lower() for value in metadata_list(doc.metadata, "traces_to")
        }:
            result.append((path, doc.metadata))
    return result


def apply_acceptance(
    root: Path,
    milestone_id: str,
    *,
    source_sha: str,
    evidence_ref: str,
    semantic_review_ref: str | None,
    owner_confirmation: str,
    accepted_at: str,
    evidence_data: dict[str, object] | None = None,
    semantic_review_data: dict[str, object] | None = None,
    evidence_digest: str | None = None,
    semantic_review_digest: str | None = None,
    server_source: dict[str, object] | None = None,
) -> list[str]:
    provenance_errors = validate_server_source(
        server_source, expected_sha=source_sha, require_artifact=True
    )
    if provenance_errors:
        raise ValueError("Acceptance требует полный server_source: " + "; ".join(provenance_errors))
    record_path = root / "work" / "acceptance" / f"{milestone_id.lower()}.json"
    if record_path.exists():
        raise ValueError(f"Запись принятия уже существует: {relative_posix(record_path, root)}")
    linked_tasks = _tasks_for_milestone(root, milestone_id)
    unfinished = [
        str(metadata.get("id", relative_posix(path, root)))
        for path, metadata in linked_tasks
        if str(metadata.get("work_state", "")).lower() != "completed"
    ]
    if unfinished:
        raise ValueError("Нельзя принять milestone: не завершены TASK " + ", ".join(unfinished))
    validate_confirmation(milestone_id, owner_confirmation)
    if (
        not isinstance(evidence_data, dict)
        or evidence_data.get("acceptance_state") != "ready-for-semantic-review"
        or str(evidence_data.get("git_sha", "")).lower() != source_sha.lower()
    ):
        raise ValueError("Acceptance требует техническое evidence ready на source_git_sha")
    if (
        not isinstance(semantic_review_data, dict)
        or semantic_review_data.get("result") != "pass"
        or str(semantic_review_data.get("milestone", "")).lower() != milestone_id.lower()
        or str(semantic_review_data.get("reviewed_sha", "")).lower() != source_sha.lower()
    ):
        raise ValueError("Acceptance требует semantic review pass на source_git_sha")

    changed: list[str] = []
    planned_writes: list[tuple[Path, str]] = []
    milestones_path = root / "milestones.md"
    milestones_text = read_text(milestones_path)
    accepted_date = accepted_at[:10]
    new_milestones = _replace_front_matter_updated(
        _replace_milestone_work_state(milestones_text, milestone_id),
        accepted_date,
    )
    if new_milestones != milestones_text:
        planned_writes.append((milestones_path, new_milestones))

    if milestone_id.lower() == "m01":
        for path in sorted((root / "adr").glob("adr_*.md")):
            original = read_text(path)
            metadata = load_document(path).metadata
            if "m01" not in {value.lower() for value in metadata_list(metadata, "traces_to")}:
                continue
            updated = _replace_front_matter_state(
                original,
                field="decision_state",
                allowed_from={"proposed"},
                target="accepted",
                updated=accepted_date,
            )
            if updated != original:
                planned_writes.append((path, updated))

    technical_evidence: dict[str, object] = {
        "git_sha": source_sha,
        "sha256": evidence_digest or "not-recorded",
    }
    for key in (
        "acceptance_state",
        "timestamp",
        "environment",
        "quality_profiles",
        "coverage_base",
        "coverage",
        "evidence",
        "tests",
    ):
        if key in evidence_data:
            technical_evidence[key] = evidence_data[key]
    if server_source:
        technical_evidence["server_source"] = server_source

    semantic_evidence: dict[str, object] = {
        **semantic_review_data,
        "sha256": semantic_review_digest or "not-recorded",
    }

    record = {
        "schema_version": 2,
        "type": "milestone_acceptance",
        "milestone": milestone_id.lower(),
        "decision": "accepted",
        "owner_confirmation": owner_confirmation,
        "source_git_sha": source_sha,
        "technical_evidence": technical_evidence,
        "semantic_review": semantic_evidence,
        "accepted_at": accepted_at,
    }
    for path, content in planned_writes:
        if atomic_write(path, content):
            changed.append(relative_posix(path, root))
    atomic_write(record_path, json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    changed.append(relative_posix(record_path, root))
    return sorted(dict.fromkeys(changed))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Подготовить owner-controlled acceptance transition"
    )
    parser.add_argument("--milestone", required=True)
    parser.add_argument("--owner-confirmation", required=True)
    parser.add_argument("--evidence", required=True, help="Путь к evidence bundle JSON")
    parser.add_argument(
        "--semantic-review", help="SHA-bound semantic review JSON; обязателен для каждого этапа"
    )
    parser.add_argument(
        "--evidence-run-url", required=True, help="Постоянная ссылка на серверный запуск проверки"
    )
    parser.add_argument("--evidence-run-id", required=True, help="Числовой ID серверного запуска")
    parser.add_argument("--evidence-repository", required=True, help="GitHub repository owner/name")
    parser.add_argument("--evidence-workflow", required=True, help="Имя GitHub Actions workflow")
    parser.add_argument("--evidence-event-sha", required=True, help="SHA события GitHub Actions")
    parser.add_argument(
        "--evidence-artifact-id", required=True, help="Идентификатор серверного артефакта"
    )
    parser.add_argument(
        "--evidence-artifact-digest", required=True, help="Контрольная сумма серверного артефакта"
    )
    args = parser.parse_args()

    require_supported_python()

    root = find_project_root(Path.cwd())
    milestone_id = str(args.milestone).lower()
    confirmation = str(args.owner_confirmation)
    validate_confirmation(milestone_id, confirmation)

    branch = _git_branch(root)
    if branch in {"", "main", "master"}:
        raise SystemExit(
            "Acceptance transition запрещён на default branch. Создайте отдельную ветку."
        )

    evidence_path = Path(args.evidence)
    if not evidence_path.is_absolute():
        evidence_path = root / evidence_path
    evidence = validate_evidence_bundle(root, evidence_path, milestone_id)
    if not args.semantic_review:
        raise SystemExit(f"Для {milestone_id} обязателен --semantic-review")
    semantic_path = Path(args.semantic_review)
    if not semantic_path.is_absolute():
        semantic_path = root / semantic_path
    semantic_review = validate_semantic_review(root, semantic_path, milestone_id)

    server_source = {
        "repository": args.evidence_repository,
        "workflow": args.evidence_workflow,
        "run_id": args.evidence_run_id,
        "run_url": args.evidence_run_url,
        "event_sha": args.evidence_event_sha,
        "artifact_id": args.evidence_artifact_id,
        "artifact_digest": args.evidence_artifact_digest,
    }
    bundle_source = evidence.get("server_source")
    for key in ("repository", "workflow", "run_id", "run_url", "event_sha"):
        if not isinstance(bundle_source, dict) or str(bundle_source.get(key, "")) != str(
            server_source[key]
        ):
            raise ValueError(f"CLI server_source.{key} не совпадает с evidence bundle")

    changed = apply_acceptance(
        root,
        milestone_id,
        source_sha=str(evidence["git_sha"]),
        evidence_ref=str(args.evidence),
        semantic_review_ref=str(args.semantic_review),
        owner_confirmation=confirmation,
        accepted_at=now_iso_minutes(),
        evidence_data=evidence,
        semantic_review_data=semantic_review,
        evidence_digest=_file_sha256(evidence_path),
        semantic_review_digest=_file_sha256(semantic_path),
        server_source=server_source,
    )
    print(f"Acceptance transition prepared for {milestone_id}.")
    for path in changed:
        print(f"  changed: {path}")
    print(
        "Commit/push/merge не выполнялись. Пересоберите generated views, запустите Project check и откройте PR."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
