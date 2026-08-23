from __future__ import annotations

import os
import platform
import re
from collections import Counter
from pathlib import Path
from typing import TypedDict, cast

from operations.scripts.common.project import (
    iter_files,
    now_iso_minutes,
    relative_posix,
    run_command,
)
from operations.scripts.common.status_types import (
    MilestoneItem,
    MilestonesReport,
    TaskItem,
    TasksReport,
    TestSpecItem,
    TestSpecsReport,
    UnitSummary,
)
from operations.scripts.documents.index import is_primary_markdown
from operations.scripts.documents.metadata import load_document, metadata_list, typed_state
from operations.scripts.documents.traceability import (
    collect_traceable_elements,
    parse_scope_references,
)
from operations.scripts.quality.registry import (
    evaluate_milestone_quality,
    evidence_results,
    impacted_profiles,
    load_quality_registry,
    profiles_for_milestone,
    uncovered_paths,
)
from operations.scripts.tasks.generate import collect_tasks
from operations.scripts.tasks.semantics import delivery_closure, validate_task_semantics

MILESTONE_HEADING = re.compile(r"^##\s+(m\d{2})\s+—\s+(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
MILESTONE_WORK_STATE = re.compile(r"(?m)^-\s+work_state:\s+`?([a-z-]+)`?\s*$", re.IGNORECASE)
MILESTONE_WORK_STATES = {"planned", "in-progress", "blocked", "completed"}
V1_BOUNDARY = re.compile(r"поставка\s+завершается\s+после\s+`?(m\d{2})`?", re.IGNORECASE)
UNIT_RAN = re.compile(r"Ran\s+(\d+)\s+tests?\s+in\s+([0-9.]+)s", re.IGNORECASE)
UNIT_FAILED = re.compile(r"FAILED\s*\(([^)]*)\)", re.IGNORECASE)
UNIT_FAILURE_LINE = re.compile(r"^(FAIL|ERROR):\s+(.+)$", re.MULTILINE)


class AcceptanceDocument(TypedDict):
    id: str
    state_field: str
    state: str
    path: str


class AcceptanceDocumentsReport(TypedDict):
    count: int
    current: list[AcceptanceDocument]
    proposed_decisions: list[AcceptanceDocument]


class ChangeScopeResult(TypedDict):
    mode: str
    base_sha: str | None
    paths: list[str]
    error: str | None


class NextActionCommand(TypedDict):
    label: str
    value: str


class NextAction(TypedDict):
    actor: str
    instruction: str
    commands: list[NextActionCommand]
    requires_fresh_session: bool


class EffectiveTestItem(TestSpecItem):
    effective_result: str


class CoverageResult(TypedDict):
    scope_total: int
    scope_covered: int
    scope: list[str]
    covered: list[str]
    tracked_kind: str
    tracked_total: int
    tracked_covered: int
    tracked_targets: list[str]
    blockers: list[str]
    modes: list[str]


class CoverageBase(TypedDict):
    mode: str
    git_sha: str | None


class ProgressSnapshot(TypedDict):
    overall: str
    milestones: MilestonesReport
    current: MilestoneItem
    next_milestone: MilestoneItem | None
    tasks: TasksReport
    tests: TestSpecsReport
    checks_passed: int
    checks_total: int
    check_summary: dict[str, object]
    unit: UnitSummary
    acceptance: AcceptanceResult
    deviations: list[str]
    next_action: NextAction
    git: dict[str, object]


class AcceptanceResult(TypedDict):
    state: str
    technical_ready: bool
    accepted: bool
    pending_gates: list[str]
    owner_action: str
    tasks_total: int
    tasks_verified: int
    tests_total: int
    tests_passed: int
    tests: list[EffectiveTestItem]
    quality: dict[str, object]
    coverage: CoverageResult
    evidence_results: dict[str, dict[str, object]]
    evidence_context: dict[str, object]
    changed_paths: list[str]
    coverage_base: CoverageBase
    uncovered_paths: list[str]
    impacted_profiles: list[str]
    documents_total: int
    documents_current: int
    decisions_proposed: int
    remaining: list[str]
    blockers: list[str]


def collect_milestones(root: Path) -> MilestonesReport:
    path = root / "milestones.md"
    if not path.is_file():
        raise ValueError("Отсутствует milestones.md")
    text = path.read_text(encoding="utf-8-sig")
    matches = list(MILESTONE_HEADING.finditer(text))
    if not matches:
        raise ValueError("milestones.md не содержит m01, m02, ...")
    items: list[MilestoneItem] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.end() : end]
        state_match = MILESTONE_WORK_STATE.search(section)
        if not state_match:
            raise ValueError(f"{match.group(1).lower()}: отсутствует work_state")
        work_state = state_match.group(1).lower()
        if work_state not in MILESTONE_WORK_STATES:
            raise ValueError(f"{match.group(1).lower()}: неизвестный work_state '{work_state}'")
        items.append(
            {
                "id": match.group(1).lower(),
                "title": match.group(2).strip(),
                "work_state": work_state,
                "scope": parse_scope_references(section),
            }
        )
    current = next((item for item in items if item["work_state"] != "completed"), items[-1])
    return {
        "count": len(items),
        "items": items,
        "current": current,
        "states": dict(Counter(str(item["work_state"]) for item in items)),
    }


def v1_milestone_ids(root: Path) -> list[str]:
    """Этапы, входящие в периметр V1, по объявленной в milestones.md границе поставки.

    Граница читается из текста, а не задаётся в коде: добавление или перенос этапа
    не должно молча разойтись с тем, что показывает владельцу экран управления.
    """
    items = [str(item["id"]) for item in collect_milestones(root)["items"]]
    match = V1_BOUNDARY.search((root / "milestones.md").read_text(encoding="utf-8-sig"))
    if not match:
        return items
    boundary = match.group(1).lower()
    return items[: items.index(boundary) + 1] if boundary in items else items


def collect_test_specs(root: Path) -> TestSpecsReport:
    items: list[TestSpecItem] = []
    tests_dir = root / "work/tests"
    if tests_dir.is_dir():
        for path in sorted(tests_dir.glob("test_*.md")):
            doc = load_document(path)
            items.append(
                {
                    "id": str(doc.metadata.get("id", "")).strip(),
                    "spec_state": str(doc.metadata.get("spec_state", "")).strip().lower(),
                    "execution": str(doc.metadata.get("execution", "owner")).strip().lower()
                    or "owner",
                    "automated_evidence": str(doc.metadata.get("automated_evidence", "")).strip(),
                    "manual_evidence": str(doc.metadata.get("manual_evidence", "")).strip(),
                    "traces_to": [
                        value.strip() for value in metadata_list(doc.metadata, "traces_to")
                    ],
                    "verifies": [
                        value.strip() for value in metadata_list(doc.metadata, "verifies")
                    ],
                    "accepts": [
                        value.strip().lower() for value in metadata_list(doc.metadata, "accepts")
                    ],
                    "title": doc.title,
                    "path": path.relative_to(root).as_posix(),
                }
            )
    return {
        "count": len(items),
        "items": items,
        "states": dict(Counter(str(item["spec_state"]) for item in items)),
    }


def parse_unit_test_summary(returncode: int, output: str) -> UnitSummary:
    ran = UNIT_RAN.search(output)
    total = int(ran.group(1)) if ran else 0
    duration = float(ran.group(2)) if ran else None
    failures = 0
    failed = UNIT_FAILED.search(output)
    if failed:
        for value in re.findall(r"(?:failures|errors)=(\d+)", failed.group(1), re.IGNORECASE):
            failures += int(value)
    if returncode != 0 and failures == 0:
        failures = 1
    passed = max(total - failures, 0) if total else 0
    problems = [match.group(2).strip() for match in UNIT_FAILURE_LINE.finditer(output)][:5]
    label = (
        (f"{total}/{total} PASS" if total else "PASS")
        if returncode == 0
        else (f"{passed}/{total} PASS · {failures} FAIL" if total else "FAIL")
    )
    if duration is not None:
        label += f" · {duration:.1f}s"
    return {
        "ok": returncode == 0,
        "total": total,
        "passed": total if returncode == 0 else passed,
        "failed": failures,
        "duration": duration,
        "label": label,
        "problems": problems,
    }


def format_unit_result_ru(unit: UnitSummary) -> str:
    if unit.get("ok"):
        result = f"{unit['passed']}/{unit['total']} успешно" if unit.get("total") else "успешно"
    else:
        result = (
            f"{unit['passed']}/{unit['total']} успешно · ошибок: {unit['failed']}"
            if unit.get("total")
            else "ошибка"
        )
    duration = unit["duration"]
    if duration is not None:
        result += f" · {duration:.1f} с"
    return result


def _task_milestones(task: TaskItem) -> list[str]:
    return [
        value.lower()
        for value in task["traces_to"]
        if re.fullmatch(r"m\d{2}", value, re.IGNORECASE)
    ]


def _acceptance_documents(root: Path) -> AcceptanceDocumentsReport:
    items: list[AcceptanceDocument] = []
    for path in iter_files(root, suffixes={".md"}, include_generated=False):
        relative = relative_posix(path, root)
        if not is_primary_markdown(relative) or relative.startswith(("work/tasks/", "work/tests/")):
            continue
        doc = load_document(path)
        state_field, state = typed_state(doc.metadata, relative)
        items.append(
            {
                "id": str(doc.metadata.get("id", "")).strip(),
                "state_field": state_field,
                "state": state,
                "path": relative,
            }
        )
    return {
        "count": len(items),
        "current": [item for item in items if item["state"] in {"current", "accepted"}],
        "proposed_decisions": [
            item
            for item in items
            if item["state_field"] == "decision_state" and item["state"] == "proposed"
        ],
    }


def _environment() -> dict[str, str]:
    return {
        "os": platform.system(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "runner_os": os.environ.get("RUNNER_OS", "local"),
    }


def _git_paths(root: Path, command: list[str]) -> tuple[list[str], str | None]:
    result = run_command(command, cwd=root, timeout=30)
    if not result.ok:
        detail = result.stderr.strip() or result.stdout.strip() or "неизвестная ошибка Git"
        return [], detail
    return (
        [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()],
        None,
    )


def _change_scope(root: Path, milestone_id: str) -> ChangeScopeResult:
    """Вернуть все пути, изменённые после принятия предыдущего этапа.

    Для m01 проверяется всё отслеживаемое дерево. Следующие этапы начинаются с
    коммита, впервые добавившего запись принятия предыдущего этапа. Поэтому файл
    из более раннего коммита не может скрыться за последним коммитом.
    """
    normalized = milestone_id.lower()
    match = re.fullmatch(r"m(\d{2})", normalized)
    if not match:
        return {
            "mode": "invalid",
            "base_sha": None,
            "paths": [],
            "error": f"Некорректный этап: {milestone_id}",
        }

    number = int(match.group(1))
    if number == 1:
        paths, error = _git_paths(root, ["git", "ls-files"])
        return {
            "mode": "tracked_tree",
            "base_sha": "repository-start",
            "paths": paths,
            "error": error,
        }

    previous = f"m{number - 1:02d}"
    record = f"work/acceptance/{previous}.json"
    commits, error = _git_paths(
        root,
        ["git", "log", "--diff-filter=A", "--format=%H", "--", record],
    )
    if error:
        return {"mode": "accepted_milestone", "base_sha": None, "paths": [], "error": error}
    if not commits:
        return {
            "mode": "accepted_milestone",
            "base_sha": None,
            "paths": [],
            "error": f"Не найден коммит принятия предыдущего этапа {previous}: {record}",
        }
    base_sha = commits[-1]
    paths, error = _git_paths(root, ["git", "diff", "--name-only", base_sha, "HEAD"])
    return {"mode": "accepted_milestone", "base_sha": base_sha, "paths": paths, "error": error}


def build_owner_next_action(
    milestone_id: str,
    *,
    resume_target: str,
    requires_fresh_session: bool,
    owner_action: str = "none",
) -> NextAction:
    """Return the single owner-facing action model used by every status view."""
    if owner_action != "none":
        return {
            "actor": "владелец",
            "instruction": f"Выбрать решение по этапу `{milestone_id}`.",
            "commands": [
                {"label": "Принять этап", "value": owner_action},
                {
                    "label": "Вернуть на доработку",
                    "value": f"ВОЗВРАЩАЮ {milestone_id}: <что исправить>",
                },
            ],
            "requires_fresh_session": False,
        }

    instruction = "Отправьте агенту одну команду."
    if requires_fresh_session:
        instruction = "Откройте новый сеанс агента без истории разработки и отправьте одну команду."
    return {
        "actor": "владелец",
        "instruction": instruction,
        "commands": [{"label": "Продолжить", "value": f"ПРОДОЛЖАЙ {resume_target}"}],
        "requires_fresh_session": requires_fresh_session,
    }


def _coverage(
    *,
    current: MilestoneItem,
    current_tasks: list[TaskItem],
    effective_tests: list[EffectiveTestItem],
    profiles: list[tuple[str, dict[str, object]]],
    evidence: dict[str, dict[str, object]],
    traceability_records: dict[str, dict[str, object]] | None = None,
) -> CoverageResult:
    scope = current["scope"]
    blockers: list[str] = []
    covered: set[str] = set()
    foundation_targets: list[str] = []
    foundation_covered: set[str] = set()

    coverage_modes = {str(raw.get("scope_coverage", "task_test")) for _, raw in profiles}
    global_evidence: list[str] = []
    for _, raw in profiles:
        if str(raw.get("scope_coverage", "task_test")) == "global_evidence":
            raw_scope_evidence = raw.get("scope_evidence", [])
            if isinstance(raw_scope_evidence, list):
                global_evidence.extend(str(value) for value in raw_scope_evidence if str(value))
            if not scope:
                # `raw` comes from quality_registry.json via registry.py, which is not
                # yet typed beyond dict[str, object]; "paths" is documented there as a
                # list of path patterns.
                raw_paths = cast(list[object], raw.get("paths", []))
                for value in raw_paths:
                    target = f"path:{value}"
                    if str(value) and target not in foundation_targets:
                        foundation_targets.append(target)

    if "global_evidence" in coverage_modes:
        missing = [
            item
            for item in dict.fromkeys(global_evidence)
            if str(evidence.get(item, {}).get("result", "missing")) != "passed"
        ]
        if missing:
            blockers.append("Глобальные доказательства покрытия не прошли: " + ", ".join(missing))
        else:
            covered.update(scope)
            foundation_covered.update(foundation_targets)

    if "task_test" in coverage_modes or not coverage_modes:
        passed_tests = [
            test for test in effective_tests if test.get("effective_result") == "passed"
        ]
        for item in scope:
            tasks = [
                task
                for task in current_tasks
                if item
                in (
                    delivery_closure(
                        traceability_records,
                        {str(task.get("component", "")).upper()},
                    )
                    if traceability_records and task.get("component")
                    else set(str(value) for value in task.get("implements", []))
                )
            ]
            if not tasks:
                blockers.append(
                    f"Элемент состава {item} не реализуется ни одной задачей текущего этапа."
                )
                continue
            if any(
                item
                in (
                    delivery_closure(
                        traceability_records,
                        {str(value) for value in test.get("verifies", [])},
                    )
                    if traceability_records
                    else set(str(value) for value in test.get("verifies", []))
                )
                and any(
                    str(task["id"]) in set(str(value) for value in test.get("traces_to", []))
                    for task in tasks
                )
                for test in passed_tests
            ):
                covered.add(item)
            else:
                blockers.append(
                    f"Элемент состава {item} не покрыт успешной проверкой и доказательством."
                )

    passed_tests = [test for test in effective_tests if test.get("effective_result") == "passed"]
    for task in current_tasks:
        for item in [str(value) for value in task.get("implements", [])]:
            linked = [
                test
                for test in passed_tests
                if str(task["id"]) in set(str(value) for value in test.get("traces_to", []))
            ]
            if not any(
                item in set(str(value) for value in test.get("verifies", [])) for test in linked
            ):
                blockers.append(
                    f"{task['id']}: реализует {item} без успешной проверки этого требования."
                )

    tracked_targets = scope if scope else foundation_targets
    tracked_covered = covered if scope else foundation_covered

    return {
        "scope_total": len(scope),
        "scope_covered": len(covered),
        "scope": scope,
        "covered": sorted(covered),
        "tracked_kind": "milestone_scope" if scope else "foundation_paths",
        "tracked_total": len(tracked_targets),
        "tracked_covered": len(tracked_covered),
        "tracked_targets": tracked_targets,
        "blockers": list(dict.fromkeys(blockers)),
        "modes": sorted(coverage_modes),
    }


def evaluate_acceptance(
    root: Path,
    *,
    milestones: MilestonesReport,
    tasks: TasksReport,
    tests: TestSpecsReport,
    check_summary: dict[str, object],
    unit_summary: UnitSummary,
    git: dict[str, object],
) -> AcceptanceResult:
    current = milestones["current"]
    current_id = current["id"]
    current_work_state = current["work_state"]
    current_tasks = [item for item in tasks["tasks"] if current_id in _task_milestones(item)]
    task_ids = {item["id"] for item in current_tasks}
    current_tests = [
        item
        for item in tests["items"]
        if current_id in {value.lower() for value in item["accepts"]}
        or task_ids.intersection(set(item["traces_to"]))
    ]

    context: dict[str, object] = {
        "git_sha": str(git.get("commit", "unknown")),
        "timestamp": now_iso_minutes(),
        "environment": _environment(),
    }
    registry = load_quality_registry(root)
    results = evidence_results(
        registry,
        root=root,
        check_summary=check_summary,
        unit_summary=unit_summary,
        context=context,
    )
    effective_tests: list[EffectiveTestItem] = []
    for item in current_tests:
        execution = item["execution"] or "owner"
        evidence_id = (
            item["automated_evidence"] if execution == "automated" else item["manual_evidence"]
        )
        if evidence_id:
            result = str(results.get(evidence_id, {}).get("result", "missing"))
        else:
            result = "missing"
        effective_tests.append({**item, "effective_result": result})

    passed_ids = {item["id"] for item in effective_tests if item["effective_result"] == "passed"}
    verified_tasks = 0
    for task in current_tasks:
        linked = {test["id"] for test in current_tests if task["id"] in set(test["traces_to"])}
        if linked and linked.issubset(passed_ids):
            verified_tasks += 1

    quality = evaluate_milestone_quality(
        root,
        current_id,
        check_summary=check_summary,
        unit_summary=unit_summary,
        context=context,
    )
    profiles = profiles_for_milestone(registry, current_id)
    coverage_modes = {str(raw.get("scope_coverage", "task_test")) for _, raw in profiles}
    requires_project_tasks = "task_test" in coverage_modes or not coverage_modes
    coverage = _coverage(
        current=current,
        current_tasks=current_tasks,
        effective_tests=effective_tests,
        profiles=profiles,
        evidence=results,
        traceability_records=collect_traceable_elements(root),
    )
    # `quality` comes from evaluate_milestone_quality() in registry.py, not yet typed
    # beyond dict[str, object]; "blockers" is documented there as list[str].
    quality_blockers = cast(list[str], quality["blockers"])
    blockers: list[str] = [*quality_blockers, *coverage["blockers"]]
    if requires_project_tasks:
        blockers.extend(validate_task_semantics(root, current_id))

    change_scope = _change_scope(root, current_id)
    changed = list(change_scope["paths"])
    path_gaps = uncovered_paths(profiles, changed)
    if current_work_state in {"in-progress", "blocked"} and change_scope.get("error"):
        blockers.append(
            "Не удалось определить полную область изменений этапа: " + str(change_scope["error"])
        )
    if current_work_state in {"in-progress", "blocked"} and path_gaps:
        blockers.append("Изменённые пути вне активного профиля качества: " + ", ".join(path_gaps))
    if current_work_state == "planned":
        blockers.append(
            "Этап ещё запланирован: перед реализацией нужны окончательный состав и активный профиль качества."
        )

    docs = _acceptance_documents(root)
    for task in current_tasks:
        if str(task.get("work_state")) == "blocked":
            blockers.append(f"{task['id']} заблокирована.")
    for test in effective_tests:
        if test["effective_result"] in {"failed", "blocked", "missing"}:
            blockers.append(f"{test['id']}: {test['effective_result']}.")
    if current_work_state != "planned":
        if requires_project_tasks and not current_tasks:
            blockers.append("Для текущего продуктового этапа не зарегистрированы TASK.")
        elif current_tasks and verified_tasks != len(current_tasks):
            blockers.append(f"Технически подтверждено TASK: {verified_tasks}/{len(current_tasks)}.")
        unfinished_tasks = [
            str(task["id"]) for task in current_tasks if str(task.get("work_state")) != "completed"
        ]
        if unfinished_tasks:
            blockers.append("Не завершены TASK: " + ", ".join(unfinished_tasks) + ".")

    accepted = current_work_state == "completed"
    eligible = current_work_state == "in-progress"
    technical_ready = eligible and not blockers and bool(current_tests)
    # Каждый этап проходит смысловую проверку перед принятием, поэтому одной
    # только технической готовности недостаточно: "ready-for-acceptance" без
    # смысловой проверки больше не наступает ни для одного этапа.
    semantic_review_pending = technical_ready and not accepted
    state = (
        "accepted"
        if accepted
        else "ready-for-semantic-review"
        if semantic_review_pending
        else "not-ready"
    )
    remaining = list(dict.fromkeys(blockers))
    pending_gates = ["semantic_review"] if semantic_review_pending else []
    return {
        "state": state,
        "technical_ready": technical_ready,
        "accepted": accepted,
        "pending_gates": pending_gates,
        "owner_action": "none",
        "tasks_total": len(current_tasks),
        "tasks_verified": verified_tasks,
        "tests_total": len(current_tests),
        "tests_passed": sum(1 for item in effective_tests if item["effective_result"] == "passed"),
        "tests": effective_tests,
        "quality": quality,
        "coverage": coverage,
        "evidence_results": results,
        "evidence_context": context,
        "changed_paths": changed,
        "coverage_base": {
            "mode": str(change_scope.get("mode", "unknown")),
            "git_sha": change_scope.get("base_sha"),
        },
        "uncovered_paths": path_gaps,
        "impacted_profiles": impacted_profiles(registry, changed),
        "documents_total": int(docs["count"]),
        "documents_current": len(docs["current"]),
        "decisions_proposed": len(docs["proposed_decisions"]),
        "remaining": remaining,
        "blockers": remaining,
    }


def build_progress_snapshot(
    root: Path,
    *,
    check_summary: dict[str, object],
    test_returncode: int,
    test_output: str,
    git: dict[str, object],
) -> ProgressSnapshot:
    milestones = collect_milestones(root)
    tasks = collect_tasks(root)
    tests = collect_test_specs(root)
    unit = parse_unit_test_summary(test_returncode, test_output)
    acceptance = evaluate_acceptance(
        root,
        milestones=milestones,
        tasks=tasks,
        tests=tests,
        check_summary=check_summary,
        unit_summary=unit,
        git=git,
    )
    current = milestones["current"]
    current_index = next(
        index for index, item in enumerate(milestones["items"]) if item["id"] == current["id"]
    )
    next_milestone = (
        milestones["items"][current_index + 1]
        if current_index + 1 < len(milestones["items"])
        else None
    )
    # check_summary is external input (parsed from check.py's JSON output), not yet
    # typed beyond dict[str, object].
    raw_checks = cast(list[object], check_summary.get("checks", []))
    checks: list[dict[str, object]] = [item for item in raw_checks if isinstance(item, dict)]
    deviations: list[str] = []
    for item in checks:
        raw_errors = item.get("errors")
        for error in raw_errors if isinstance(raw_errors, list) else []:
            deviations.append(f"{item.get('name')}: {error}")
        raw_warnings = item.get("warnings")
        for warning in raw_warnings if isinstance(raw_warnings, list) else []:
            deviations.append(f"{item.get('name')}: ПРЕДУПРЕЖДЕНИЕ: {warning}")
    for problem in unit["problems"]:
        deviations.append(f"модульные тесты: {problem}")
    overall = "healthy" if bool(check_summary.get("ok")) and bool(unit.get("ok")) else "attention"
    current_id = str(current["id"])
    current_tasks = [item for item in tasks["tasks"] if current_id in _task_milestones(item)]
    unfinished_tasks = [
        item for item in current_tasks if str(item.get("work_state")) != "completed"
    ]
    resume_target = str(unfinished_tasks[0]["id"]) if unfinished_tasks else current_id
    next_action = build_owner_next_action(
        current_id,
        resume_target=resume_target,
        requires_fresh_session=acceptance["state"] == "ready-for-semantic-review",
        owner_action=str(acceptance["owner_action"]),
    )
    return {
        "overall": overall,
        "milestones": milestones,
        "current": current,
        "next_milestone": next_milestone,
        "tasks": tasks,
        "tests": tests,
        "checks_passed": sum(1 for item in checks if item.get("ok")),
        "checks_total": len(checks),
        "check_summary": check_summary,
        "unit": unit,
        "acceptance": acceptance,
        "deviations": deviations,
        "next_action": next_action,
        "git": git,
    }


def render_progress_sections(snapshot: ProgressSnapshot) -> str:
    current = snapshot["current"]
    next_milestone = snapshot["next_milestone"]
    acceptance = snapshot["acceptance"]
    unit = snapshot["unit"]
    next_label = f"{next_milestone['id']} — {next_milestone['title']}" if next_milestone else "—"
    pending = acceptance["pending_gates"]
    pending_labels = {
        "semantic_review": "смысловая проверка",
    }
    if acceptance["remaining"]:
        remaining = "\n".join(f"- {item}" for item in acceptance["remaining"])
    elif pending:
        remaining = (
            "Технические условия выполнены. Осталось отдельное условие: "
            + ", ".join(pending_labels.get(str(item), str(item)) for item in pending)
            + "."
        )
    else:
        remaining = "Автоматические условия готовности выполнены."
    deviations = (
        "\n".join(f"- {item}" for item in snapshot["deviations"])
        if snapshot["deviations"]
        else "Технических отклонений не обнаружено."
    )
    result_labels = {
        "passed": "пройдено",
        "failed": "ошибка",
        "missing": "нет результата",
        "blocked": "заблокировано",
    }
    class_labels = {"hard": "обязательное", "soft": "дополнительное"}
    source_labels = {"checker": "проверки проекта", "unit_tests": "модульные тесты"}

    def source_label(value: object) -> str:
        source = str(value)
        if source.startswith("record:"):
            return "структурированная запись"
        return source_labels.get(source, source)

    # `quality` comes from evaluate_milestone_quality() in registry.py, not yet typed
    # beyond dict[str, object]; "evidence" is documented there as a list of records.
    quality_evidence = cast(list[dict[str, object]], acceptance["quality"].get("evidence", []))
    evidence_rows = (
        "\n".join(
            f"| `{row['id']}` | {result_labels.get(str(row['result']), str(row['result']))} | "
            f"{class_labels.get(str(row['class']), str(row['class']))} | "
            f"{source_label(row['source'])} | `{str(row.get('git_sha', 'unknown'))[:12]}` |"
            for row in quality_evidence
        )
        or "| — | — | — | — | — |"
    )
    coverage = acceptance["coverage"]
    coverage_label = (
        "Области основы" if coverage["tracked_kind"] == "foundation_paths" else "Состав этапа"
    )
    profile_labels = {"foundation": "основа"}
    impacted = (
        ", ".join(profile_labels.get(item, item) for item in acceptance["impacted_profiles"]) or "—"
    )
    work_state_labels = {
        "planned": "запланирован",
        "in-progress": "в работе",
        "blocked": "заблокирован",
        "completed": "завершён",
    }
    acceptance_state_labels = {
        "accepted": "принят",
        "ready-for-semantic-review": "готов к смысловой проверке",
        "ready-for-acceptance": "готов к принятию",
        "not-ready": "не готов",
    }
    unit_result = format_unit_result_ru(unit)
    next_action = snapshot["next_action"]
    action_commands = "\n".join(
        f"- {item['label']}: `{item['value']}`." for item in next_action["commands"]
    )
    return f"""## Прогресс

| Параметр | Значение |
|---|---|
| Общее состояние | **{"норма" if snapshot["overall"] == "healthy" else "требуется внимание"}** |
| Текущий этап | `{current["id"]}` — {current["title"]} |
| Рабочее состояние этапа | **{work_state_labels.get(str(current["work_state"]), str(current["work_state"]))}** |
| Следующий этап | {next_label} |
| Задачи подтверждены | `{acceptance["tasks_verified"]}/{acceptance["tasks_total"]}` |
| Проверки пройдены | `{acceptance["tests_passed"]}/{acceptance["tests_total"]}` |
| {coverage_label} | `{coverage.get("tracked_covered", coverage["scope_covered"])}/{coverage.get("tracked_total", coverage["scope_total"])}` |
| Затронутые профили качества | {impacted} |

## Качество

| Проверка | Результат |
|---|---|
| Проверки проекта | `{snapshot["checks_passed"]}/{snapshot["checks_total"]} успешно` |
| Модульные тесты | `{unit_result}` |

### Обязательные доказательства

| Доказательство | Результат | Обязательность | Источник | Редакция Git |
|---|---|---|---|---|
{evidence_rows}

## Приёмка

| Параметр | Значение |
|---|---|
| Этап | `{current["id"]}` |
| Состояние принятия | **{acceptance_state_labels.get(str(acceptance["state"]), str(acceptance["state"]))}** |
| Актуальные первичные документы | `{acceptance["documents_current"]}` |
| Предлагаемые решения | `{acceptance["decisions_proposed"]}` |

{remaining}

## Требует внимания

{deviations}

## Следующее действие

- Исполнитель: **{next_action["actor"]}**.
- Действие: {next_action["instruction"]}
{action_commands}
"""
