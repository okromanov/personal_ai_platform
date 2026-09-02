from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import (
    find_project_root,
    require_supported_python,
    run_command,
)
from operations.scripts.documents.index import is_primary_markdown
from operations.scripts.quality.registry import DERIVED_PATH_PATTERNS, validate_server_source
from operations.scripts.status.generate_project_status import collect_milestones
from operations.scripts.tasks.generate import TERMINAL_STATES, collect_tasks

UPDATED_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
AUDIT_HISTORY_PATH = re.compile(r"^work/audit/audit_baseline_\d{4}_\d{2}_\d{2}\.md$")
AUDIT_HISTORY_PREFIX = "work/audit/audit_baseline_"
MILESTONE_WORK_STATE = re.compile(r"(?m)^-\s+work_state:\s+`?([a-z-]+)`?\s*$", re.IGNORECASE)
# Документы, которые задают полномочия агента, владельца и правила изменения.
# Служебная правка не создаёт TASK, поэтому границы путей их не покрывают —
# видимость обеспечивается обязательной сменой версии.
AUTHORITY_DOCUMENTS = frozenset(
    {
        "project_rules.md",
        "AGENTS.md",
        "operations/change_process.md",
        "specifications/business_requirements.md",
        "specifications/threat_model.md",
        "specifications/system_specification.md",
        "specifications/architecture_baseline.md",
        "specifications/infrastructure_baseline.md",
    }
)

MAINTENANCE_PATH_PATTERNS = [
    ".claude/**",
    ".github/**",
    ".gitleaksignore",
    ".gitignore",
    "AGENTS.md",
    "milestones.md",
    "operations/**",
    "project_rules.md",
    "pyproject.toml",
    # Архитектурные схемы — производное представление спецификаций
    # (architecture_diagram_style_guide.md §1: "не отдельный источник
    # истины"), а не продуктовая поставка, поэтому границы задач их не
    # покрывают — так же, как operations/**.
    "work/artefacts/**",
    "work/acceptance/**",
    "work/audit/**",
    "work/evidence/**",
    "work/procedures/**",
    "work/tasks/**",
    "work/tests/**",
]


def _normalize(path: str) -> str:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.lstrip("/")


def _matches(path: str, patterns: list[str]) -> bool:
    # fnmatchcase: границы TASK обязаны совпадать на Windows и Linux, а fnmatch
    # применяет os.path.normcase и на Windows игнорирует регистр пути.
    normalized = _normalize(path)
    return any(fnmatch.fnmatchcase(normalized, _normalize(pattern)) for pattern in patterns)


def _milestone_declares_product_scope(root: Path) -> bool:
    """Объявляет ли активный этап продуктовый состав.

    Неизвестное состояние трактуется как продуктовое: ослаблять границы из-за
    нечитаемого плана нельзя.
    """
    try:
        return bool(collect_milestones(root)["current"].get("scope"))
    except Exception:
        return True


def _restore_front_field(text: str, field: str, expected: str, original: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(field)}:\s*([^\n]+)\s*$", text)
    if not match or match.group(1).strip().strip("`\"'").lower() != expected.lower():
        return None
    return text[: match.start(1)] + original + text[match.end(1) :]


def _exact_acceptance_document_change(
    before: str, after: str, *, milestone_id: str, adr: bool
) -> bool:
    """Allow only the state transition and front-matter updated date."""
    before_updated = _front_matter_field(before, "updated")
    after_updated = _front_matter_field(after, "updated")
    if not UPDATED_PATTERN.fullmatch(before_updated) or not UPDATED_PATTERN.fullmatch(
        after_updated
    ):
        return False
    restored = _restore_front_field(after, "updated", after_updated, before_updated)
    if restored is None:
        return False
    if adr:
        before_state = _front_matter_field(before, "decision_state")
        restored = _restore_front_field(restored, "decision_state", "accepted", before_state)
        return before_state == "proposed" and restored == before
    heading = re.compile(rf"(?m)^##\s+{re.escape(milestone_id)}\s+—\s+.+$")
    old_heading = heading.search(before)
    new_heading = heading.search(restored)
    if not old_heading or not new_heading:
        return False
    old_state = MILESTONE_WORK_STATE.search(before, old_heading.end())
    new_state = MILESTONE_WORK_STATE.search(restored, new_heading.end())
    if not old_state or not new_state:
        return False
    if old_state.group(1).lower() != "in-progress" or new_state.group(1).lower() != "completed":
        return False
    restored = restored[: new_state.start(1)] + "in-progress" + restored[new_state.end(1) :]
    return restored == before


def _controlled_acceptance_paths(
    root: Path, base: str, head: str, changed_paths: list[str]
) -> set[str]:
    """Recognise a cryptographically bound acceptance transition, path by path."""
    allowed: set[str] = set()
    changed = {_normalize(value) for value in changed_paths}
    for record_path in sorted(
        path for path in changed if re.fullmatch(r"work/acceptance/m\d{2}\.json", path)
    ):
        if _blob_at(root, base, record_path) is not None:
            continue
        raw = _blob_at(root, head, record_path)
        try:
            record = json.loads(raw or "")
        except (TypeError, ValueError):
            continue
        milestone_id = record_path.rsplit("/", 1)[-1].removesuffix(".json")
        source_sha = str(record.get("source_git_sha", "")).lower()
        technical = record.get("technical_evidence", {})
        semantic = record.get("semantic_review", {})
        if (
            not isinstance(record, dict)
            or record.get("schema_version") != 2
            or record.get("type") != "milestone_acceptance"
            or str(record.get("milestone", "")).lower() != milestone_id
            or record.get("decision") != "accepted"
            or record.get("owner_confirmation") != f"ПРИНИМАЮ {milestone_id}"
            or not re.fullmatch(r"[0-9a-f]{40}", source_sha)
            or not isinstance(technical, dict)
            or str(technical.get("git_sha", "")).lower() != source_sha
            or technical.get("acceptance_state") != "ready-for-semantic-review"
            or not isinstance(semantic, dict)
            or semantic.get("result") != "pass"
            or str(semantic.get("milestone", "")).lower() != milestone_id
            or str(semantic.get("reviewed_sha", "")).lower() != source_sha
            or validate_server_source(
                technical.get("server_source"), expected_sha=source_sha, require_artifact=True
            )
        ):
            continue
        ancestor = run_command(["git", "merge-base", "--is-ancestor", source_sha, head], cwd=root)
        if not ancestor.ok:
            continue
        milestone_before = _blob_at(root, source_sha, "milestones.md")
        milestone_after = _blob_at(root, head, "milestones.md")
        if (
            milestone_before is None
            or milestone_after is None
            or not _exact_acceptance_document_change(
                milestone_before, milestone_after, milestone_id=milestone_id, adr=False
            )
        ):
            continue
        candidate = {record_path, "milestones.md"}
        if milestone_id == "m01":
            for path in sorted(
                value for value in changed if value.startswith("adr/adr_") and value.endswith(".md")
            ):
                before = _blob_at(root, source_sha, path)
                after = _blob_at(root, head, path)
                if (
                    before is None
                    or after is None
                    or "m01"
                    not in {
                        value.lower() for value in re.findall(r"(?m)^\s*-\s+(m\d{2})\s*$", after)
                    }
                ):
                    continue
                if _exact_acceptance_document_change(
                    before, after, milestone_id=milestone_id, adr=True
                ):
                    candidate.add(path)
        allowed.update(candidate)
    return allowed


def validate_change_scope(
    root: Path,
    changed_paths: list[str],
    *,
    base: str | None = None,
    head: str | None = None,
) -> list[str]:
    """Проверить, что каждый путь поставки продукта разрешён одной актуальной TASK.

    Пока активный этап не объявляет продуктовый состав, поставки продукта нет:
    правка спецификаций относится к базовой редакции и покрывается профилем
    основы, а не карточкой задачи. Требовать TASK в этом состоянии — значит
    блокировать работу над основой требованием, которое правила прямо не ставят.

    `AUTHORITY_DOCUMENTS` исключены из этой проверки безусловно, а не только
    пока этап не объявил продуктовый состав: правку authority-документа видно
    через обязательную смену версии (`validate_document_metadata`), а не через
    границы TASK — так же, как остальные пути `MAINTENANCE_PATH_PATTERNS`.
    """
    normalized_paths = sorted(
        dict.fromkeys(_normalize(path) for path in changed_paths if path.strip())
    )
    controlled = (
        _controlled_acceptance_paths(root, base, head, normalized_paths) if base and head else set()
    )
    substantive = [
        path
        for path in normalized_paths
        if not _matches(path, list(DERIVED_PATH_PATTERNS)) and path not in controlled
    ]
    project_paths = [
        path
        for path in substantive
        if not _matches(path, MAINTENANCE_PATH_PATTERNS) and path not in AUTHORITY_DOCUMENTS
    ]
    if not project_paths:
        return []
    if not _milestone_declares_product_scope(root):
        return []
    tasks = collect_tasks(root)["tasks"]
    changed = set(normalized_paths)
    eligible = [
        task
        for task in tasks
        if str(task["work_state"]) not in TERMINAL_STATES or str(task["path"]) in changed
    ]
    errors: list[str] = []
    if not eligible:
        return ["Изменение продукта не покрыто активной либо изменяемой TASK."]
    for path in project_paths:
        covering = [
            str(task["id"])
            for task in eligible
            if _matches(path, [str(value) for value in task.get("allowed_paths", [])])
        ]
        if not covering:
            errors.append(f"{path}: путь не входит в allowed_paths активной либо изменяемой TASK")
    return errors


def _body_after_front_matter(text: str) -> str:
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return normalized
    end = normalized.find("\n---\n", 4)
    return normalized[end + 5 :] if end != -1 else normalized


def _front_matter_field(text: str, field: str) -> str:
    match = re.search(rf"(?m)^{re.escape(field)}:\s*(\S+)\s*$", text.split("\n---", 1)[0])
    return match.group(1).strip() if match else ""


def _revision_date(root: Path, revision: str) -> str:
    result = run_command(
        ["git", "show", "-s", "--format=%ad", "--date=short", revision], cwd=root, timeout=30
    )
    return result.stdout.strip() if result.ok else ""


def _blob_at(root: Path, revision: str, path: str) -> str | None:
    result = run_command(["git", "show", f"{revision}:{path}"], cwd=root, timeout=30)
    return result.stdout if result.ok else None


def _last_change_date(root: Path, base: str, head: str, path: str) -> str:
    """Дата последнего коммита в проверяемом диапазоне, менявшего именно этот файл."""
    result = run_command(
        ["git", "log", "-1", "--format=%ad", "--date=short", f"{base}..{head}", "--", path],
        cwd=root,
        timeout=30,
    )
    return result.stdout.strip() if result.ok else ""


def validate_document_metadata(
    root: Path, base: str, head: str, changed_paths: list[str]
) -> list[str]:
    """Проверить, что изменённые документы честно отражают факт своего изменения.

    Дата `updated` обязана совпадать с датой последнего коммита, менявшего этот
    документ: правдоподобная, но неверная дата иначе не ловится ничем.
    Документы, задающие полномочия, дополнительно обязаны менять версию —
    именно так уже однажды был незаметно изменён смысл правил управления.
    """
    errors: list[str] = []
    if not _revision_date(root, base) or not _revision_date(root, head):
        return ["Не удалось определить даты базовой и проверяемой редакции"]

    for path in sorted(
        dict.fromkeys(_normalize(value) for value in changed_paths if value.strip())
    ):
        if not is_primary_markdown(path) or path.startswith("operations/templates/"):
            continue
        head_text = _blob_at(root, head, path)
        if head_text is None:
            continue
        updated = _front_matter_field(head_text, "updated")
        if not UPDATED_PATTERN.fullmatch(updated):
            errors.append(f"{path}: поле updated отсутствует или не является датой ГГГГ-ММ-ДД")
            continue
        changed_at = _last_change_date(root, base, head, path)
        if changed_at and updated != changed_at:
            errors.append(
                f"{path}: updated={updated}, а документ фактически менялся {changed_at}; "
                "дата обязана отражать день собственного изменения документа"
            )
        base_text = _blob_at(root, base, path)
        if base_text is None or path not in AUTHORITY_DOCUMENTS:
            continue
        if _body_after_front_matter(base_text) == _body_after_front_matter(head_text):
            # Исправление даты в шапке смысла правил не меняет и версии не требует.
            continue
        if _front_matter_field(base_text, "version") == _front_matter_field(head_text, "version"):
            errors.append(
                f"{path}: документ задаёт полномочия и не может меняться без новой версии; "
                "иначе смысл правил меняется незаметно для читателя"
            )
    return errors


def changed_paths_between(root: Path, base: str, head: str) -> list[str]:
    result = run_command(
        ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB", base, head],
        cwd=root,
        timeout=60,
    )
    if not result.ok:
        detail = result.stderr.strip() or result.stdout.strip() or "неизвестная ошибка Git"
        raise ValueError(f"Не удалось определить изменённые пути: {detail}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def validate_audit_history(root: Path, base: str, head: str) -> list[str]:
    """Audit snapshots are append-only: a run adds a dated file, never rewrites history."""
    result = run_command(
        [
            "git",
            "diff",
            "--name-status",
            "--find-renames",
            base,
            head,
            "--",
            "work/audit",
        ],
        cwd=root,
        timeout=60,
    )
    if not result.ok:
        detail = result.stderr.strip() or result.stdout.strip() or "неизвестная ошибка Git"
        return [f"Не удалось проверить историю аудитов: {detail}"]

    errors: list[str] = []
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        status = fields[0]
        paths = [_normalize(value) for value in fields[1:]]
        audit_paths = [path for path in paths if path.startswith(AUDIT_HISTORY_PREFIX)]
        if not audit_paths:
            continue
        if status == "A" and len(paths) == 1:
            if not AUDIT_HISTORY_PATH.fullmatch(paths[0]):
                errors.append(
                    f"{paths[0]}: новый результат аудита обязан иметь имя "
                    "audit_baseline_YYYY_MM_DD.md"
                )
            continue
        errors.append(
            f"{', '.join(audit_paths)}: датированная история аудитов неизменяема; "
            "создайте новый audit_baseline_YYYY_MM_DD.md"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Проверка покрытия путей поставки проекта карточками TASK"
    )
    parser.add_argument("--base", required=True, help="Базовый Git SHA")
    parser.add_argument("--head", default="HEAD", help="Проверяемый Git SHA")
    args = parser.parse_args()
    require_supported_python()
    root = find_project_root(Path.cwd())
    changed = changed_paths_between(root, args.base, args.head)
    errors = validate_change_scope(root, changed, base=args.base, head=args.head)
    errors.extend(validate_document_metadata(root, args.base, args.head, changed))
    errors.extend(validate_audit_history(root, args.base, args.head))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Покрытие путей поставки проекта TASK подтверждено.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
