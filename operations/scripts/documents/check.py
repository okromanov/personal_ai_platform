from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import (
    IGNORED_DIRS,
    find_project_root,
    generated_content_matches,
    iter_files,
    read_text,
    relative_posix,
    require_supported_python,
)
from operations.scripts.documents.index import is_primary_markdown, render_index
from operations.scripts.documents.links import check_markdown_links
from operations.scripts.documents.metadata import (
    STATE_FIELDS,
    STATE_VALUES,
    expected_state_field,
    load_document,
    metadata_list,
)
from operations.scripts.documents.non_markdown_index import render_non_markdown_index
from operations.scripts.documents.platform_capability import render_platfrom_capability
from operations.scripts.documents.repository_tree import (
    GENERATED_HEADER,
    render_repository_structure,
)
from operations.scripts.documents.test_catalog import render_test_catalog
from operations.scripts.documents.traceability import (
    collect_traceable_elements,
    render_traceability,
)
from operations.scripts.quality.registry import (
    load_quality_registry,
    profiles_for_milestone,
    validate_quality_registry,
)
from operations.scripts.status.generate_project_status import (
    collect_milestones,
    collect_test_specs,
    v1_milestone_ids,
)
from operations.scripts.status.human_status import render_repository_project_status
from operations.scripts.tasks.generate import TASK_ID_PATTERN, collect_tasks, render_task_index
from operations.scripts.tasks.semantics import validate_task_semantics
from operations.scripts.traceability.full_traceability import validate_full_traceability
from operations.scripts.traceability.semantic_consistency import validate_semantic_consistency

REQUIRED_METADATA = ("id", "type", "version")
VERSION_PATTERN = re.compile(r"^\d+\.\d+$")
UPDATED_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REFERENCE_KEYS = (
    "depends_on",
    "traces_to",
    "implements",
    "mitigates",
    "implemented_by",
    "verifies",
    "accepts",
)
TEST_FILE_PATTERN = re.compile(r"^test_\d{3}\.md$")
TEST_ID_PATTERN = re.compile(r"^TEST_\d{3}$")
TEST_EXECUTIONS = {"automated", "manual"}
FAMILY_WIDTH = {
    "BR": 3,
    "SYS": 3,
    "THR": 3,
    "SEC_CTL": 3,
    "INF_REQ": 3,
    "INF_CMP": 3,
    "INF_FLOW": 3,
    "ADR": 3,
    "TASK": 3,
    "TEST": 3,
}
REQUIRED_TEMPLATES = [
    "business_requirement_template.md",
    "system_requirement_template.md",
    "threat_template.md",
    "security_control_template.md",
    "infrastructure_requirement_template.md",
    "infrastructure_component_template.md",
    "infrastructure_flow_template.md",
    "milestone_template.md",
    "adr_template.md",
    "task_template.md",
    "test_template.md",
]
STABLE_CONTENT_PATHS: dict[str, object] = {}
STABLE_FORBIDDEN = [
    # Версия поставки, но не версия протокола или формата: "TLS v1.3" и "OAuth v2.0"
    # обязаны оставаться допустимыми в предметной спецификации.
    re.compile(r"\bV[123](?![\w]|\.\d)", re.IGNORECASE),
    re.compile(r"post[- ]?V1", re.IGNORECASE),
    re.compile(r"\bHermes\b", re.IGNORECASE),
    re.compile(r"Cloud\.ru", re.IGNORECASE),
    re.compile(r"\bm\d{2}\b", re.IGNORECASE),
]
DEPRECATED_TOKENS = [
    "engineering_as_code.md",
    "security_and_reliability.md",
    "adr_006_hermes_first_portable_runtime.md",
    "adr_007_code_execution_sandbox.md",
    "adr_008_telegram_vpn_and_egress.md",
    "RUNTIME_CONTRACT_GATE_1",
]
SECRET_PATTERNS = [
    re.compile(
        r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-+/]{16,}={0,2}"
    ),
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}\b"),
]
SCANNED_TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".ps1",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".txt",
    ".cfg",
    ".ini",
    ".sh",
    ".env",
    ".example",
}
THREAT_REQUIRED_LABELS = (
    "**Сценарий:**",
    "**Активы:**",
    "**Последствие:**",
    "**Остаточный риск:**",
)
ALLOWED_WORKFLOW_PERMISSIONS = {"read", "none"}


@dataclass
class CheckResult:
    name: str
    ok: bool
    errors: list[str]
    warnings: list[str]


def _result(name: str, errors: list[str], warnings: list[str] | None = None) -> CheckResult:
    return CheckResult(name=name, ok=not errors, errors=errors, warnings=warnings or [])


def _path_part_uses_snake_case(part: str) -> bool:
    if part == "AGENTS.md" or part.startswith("."):
        return True
    return part.isascii() and part == part.lower() and "-" not in part


def check_structure(root: Path) -> CheckResult:
    errors: list[str] = []
    required_dirs = [
        ".github/workflows",
        "adr",
        "specifications",
        "operations",
        "operations/templates",
        "operations/scripts",
        "operations/scripts/quality",
        "operations/scripts/evidence",
        "operations/scripts/acceptance",
        "operations/tests",
        "work",
        "work/tests",
        "generated",
        "work/acceptance",
        "work/tasks",
    ]
    required_files = [
        ".github/workflows/project_check.yml",
        "milestones.md",
        "specifications/business_requirements.md",
        "specifications/threat_model.md",
        "specifications/system_specification.md",
        "specifications/architecture_baseline.md",
        "specifications/infrastructure_baseline.md",
        "project_status.md",
        "tasks.md",
        "operations/acceptance.md",
        "operations/semantic_review.md",
        "AGENTS.md",
        "operations/local_development_windows.md",
        "operations/project_config.json",
        "operations/quality_registry.json",
        "operations/scripts/acceptance/apply.py",
        "operations/scripts/evidence/record.py",
    ] + [f"operations/templates/{name}" for name in REQUIRED_TEMPLATES]
    for relative in required_dirs:
        if not (root / relative).is_dir():
            errors.append(f"Отсутствует обязательный каталог: {relative}/")
    for relative in required_files:
        if not (root / relative).is_file():
            errors.append(f"Отсутствует обязательный файл: {relative}")
    expected_specification_files = {
        "architecture_baseline.md",
        "business_requirements.md",
        "infrastructure_baseline.md",
        "system_specification.md",
        "threat_model.md",
    }
    actual_specification_files = {path.name for path in (root / "specifications").glob("*.md")}
    if actual_specification_files != expected_specification_files:
        errors.append(
            "Каталог specifications/ должен содержать четыре базовых документа и одну системную спецификацию; "
            f"получено {sorted(actual_specification_files)}"
        )
    root_entry_names = {path.name for path in root.iterdir()}
    for name in root_entry_names:
        normalized_name = name.lower()
        if normalized_name == "readme" or normalized_name.startswith("readme."):
            errors.append(
                f"README запрещён решением владельца: {name}; "
                "единственная точка входа — project_status.md"
            )
    for forbidden in [
        "docs",
        "scripts",
        "tests",
        "operations/agent_instruction.md",
        "agent_instruction.md",
        "operations/scripts/tasks/finalize.py",
        "business_requirements.md",
        "architecture_baseline.md",
        "infrastructure_baseline.md",
        "threat_model.md",
        "specifications/core_and_channels.md",
        "specifications/context_and_evidence.md",
        "specifications/presentations.md",
        "specifications/work_and_office.md",
        "specifications/quality_and_operations.md",
        "specifications/home_and_family.md",
        "specifications/security_controls.md",
    ]:
        if (root / forbidden).exists():
            errors.append(f"Устаревший или лишний путь запрещён: {forbidden}")
    for path in root.rglob("*"):
        parts = path.relative_to(root).parts
        if any(part.lower() in IGNORED_DIRS for part in parts):
            continue
        relative = Path(*parts).as_posix()
        if any(not _path_part_uses_snake_case(part) for part in parts):
            errors.append(f"Путь должен использовать английский lower_snake_case: {relative}")
    return _result("structure", errors)


def _primary_documents(root: Path):
    for path in iter_files(root, suffixes={".md"}, include_generated=False):
        relative = relative_posix(path, root)
        if is_primary_markdown(relative):
            yield relative, load_document(path)


def _document_ids(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for relative, doc in _primary_documents(root):
        identifier = str(doc.metadata.get("id", "")).strip()
        if identifier:
            result[identifier.lower()] = relative
    return result


def _known_reference_ids(root: Path, document_ids: dict[str, str]) -> set[str]:
    known = set(document_ids)
    try:
        known.update(identifier.lower() for identifier in collect_traceable_elements(root))
    except Exception:
        pass
    try:
        known.update(str(item["id"]).lower() for item in collect_milestones(root)["items"])
    except Exception:
        pass
    return known


def check_metadata(root: Path) -> CheckResult:
    errors: list[str] = []
    identifiers: dict[str, str] = {}
    documents = []
    for relative, doc in _primary_documents(root):
        documents.append((relative, doc))
        expected_field = expected_state_field(relative)
        for key in (*REQUIRED_METADATA, expected_field):
            if key not in doc.metadata or doc.metadata[key] in (None, "", []):
                errors.append(f"{relative}: отсутствует поле '{key}'")
        if "status" in doc.metadata:
            errors.append(
                f"{relative}: универсальное поле 'status' запрещено; используйте '{expected_field}'"
            )
        present_fields = [field for field in STATE_FIELDS if field in doc.metadata]
        if present_fields != [expected_field]:
            errors.append(
                f"{relative}: ожидается только поле состояния '{expected_field}', получено {present_fields or 'ничего'}"
            )
        identifier = str(doc.metadata.get("id", "")).strip()
        normalized = identifier.lower()
        if identifier:
            if normalized in identifiers:
                errors.append(
                    f"Дублирующий document id '{identifier}': {identifiers[normalized]} и {relative}"
                )
            else:
                identifiers[normalized] = relative
        version = str(doc.metadata.get("version", "")).strip()
        if version and not VERSION_PATTERN.fullmatch(version):
            errors.append(f"{relative}: version должен иметь формат x.x, получено '{version}'")
        updated = str(doc.metadata.get("updated", "")).strip()
        # Шаблон — это форма, а не документ: он законно хранит заполнитель даты.
        if (
            updated
            and not relative.startswith("operations/templates/")
            and not UPDATED_PATTERN.fullmatch(updated)
        ):
            errors.append(
                f"{relative}: updated должен быть датой ГГГГ-ММ-ДД, получено '{updated}'; "
                "незаполненный заполнитель из шаблона недопустим в документе"
            )
        state = str(doc.metadata.get(expected_field, "")).strip().lower()
        if state and state not in STATE_VALUES[expected_field]:
            errors.append(f"{relative}: неизвестный {expected_field} '{state}'")

    known = _known_reference_ids(root, identifiers)
    for relative, doc in documents:
        for key in REFERENCE_KEYS:
            for reference in metadata_list(doc.metadata, key):
                if reference.strip().lower() not in known:
                    errors.append(f"{relative}: {key} ссылается на неизвестный id '{reference}'")
    return _result("metadata", errors)


def _expected_ids(family: str, actual: list[str]) -> set[str]:
    width = FAMILY_WIDTH[family]
    numbers = []
    for identifier in actual:
        match = re.search(r"(\d+)$", identifier)
        if not match:
            raise ValueError(f"{identifier}: идентификатор должен заканчиваться числом")
        numbers.append(int(match.group(1)))
    maximum = max(numbers)
    return {f"{family}_{index:0{width}d}" for index in range(1, maximum + 1)}


def check_traceability(root: Path) -> CheckResult:
    errors: list[str] = []
    try:
        records = collect_traceable_elements(root)
    except Exception as exc:
        return _result("traceability", [str(exc)])

    by_family: dict[str, list[str]] = {}
    for identifier, record in records.items():
        family = str(record["family"])
        if family in FAMILY_WIDTH:
            by_family.setdefault(family, []).append(identifier)
    for family in FAMILY_WIDTH:
        actual = sorted(by_family.get(family, []))
        if not actual:
            if family == "TASK":
                continue
            errors.append(f"Не найдено ни одного элемента {family}")
            continue
        expected = _expected_ids(family, actual)
        if set(actual) != expected:
            errors.append(
                f"{family} должны идти без пропусков; отсутствуют {sorted(expected - set(actual))}"
            )

    for identifier, record in records.items():
        # "relations" is always dict[str, list[str]] by construction — see
        # collect_traceable_elements() in traceability.py.
        relations = cast(dict[str, list[str]], record.get("relations", {}))
        for key, targets in relations.items():
            for target in targets:
                if target not in records:
                    errors.append(
                        f"{identifier}: {key} ссылается на неизвестный трассируемый id '{target}'"
                    )
        family = str(record["family"])
        if family == "SYS" and not any(
            target.startswith("BR_") for target in relations.get("traces_to", [])
        ):
            errors.append(f"{identifier}: SYS должен traces_to минимум один BR")
        if family == "THR":
            if not any(
                target.startswith("SEC_CTL_") for target in relations.get("mitigated_by", [])
            ):
                errors.append(f"{identifier}: THR должен иметь mitigated_by SEC_CTL")
            section = str(record.get("section", ""))
            for label in THREAT_REQUIRED_LABELS:
                if label not in section:
                    errors.append(f"{identifier}: отсутствует обязательное поле {label}")
        if family == "SEC_CTL" and not any(
            identifier
            in cast(dict[str, list[str]], other.get("relations", {})).get("mitigated_by", [])
            for other in records.values()
            if other.get("family") == "THR"
        ):
            errors.append(
                f"{identifier}: на SEC_CTL должна ссылаться минимум одна THR через mitigated_by"
            )
        if family != "THR" and (relations.get("mitigates") or relations.get("implemented_by")):
            errors.append(
                f"{identifier}: обратные mitigates/implemented_by запрещены; "
                "используйте THR.mitigated_by и связи нижнего слоя traces_to"
            )
        if family != "THR":
            # Связь «угроза — мера» хранится только как THR.mitigated_by. Ссылка нижнего
            # слоя на THR повторяет уже существующее ребро в обход канонического
            # направления и делает граф неоднозначным (governance.md, раздел 3).
            threat_targets = sorted(
                {
                    target
                    for key in ("traces_to", "implements")
                    for target in relations.get(key, [])
                    if target.startswith("THR_")
                }
            )
            if threat_targets:
                errors.append(
                    f"{identifier}: ссылка на угрозу {threat_targets} задаётся только через "
                    "THR.mitigated_by; нижний слой указывает требование или меру защиты"
                )
        if family in {"INF_CMP", "INF_FLOW"} and not any(
            target.startswith("INF_REQ_") for target in relations.get("implements", [])
        ):
            errors.append(f"{identifier}: {family} должен implements минимум один INF_REQ")
        if family == "ADR" and not relations.get("traces_to"):
            errors.append(f"{identifier}: ADR должен иметь traces_to")
        if family == "TASK" and not any(
            target.startswith("m") for target in relations.get("traces_to", [])
        ):
            errors.append(f"{identifier}: TASK должен traces_to milestone")
        if family == "TEST":
            has_task = any(target.startswith("TASK_") for target in relations.get("traces_to", []))
            accepts_milestone = any(
                str(target).lower().startswith("m") for target in relations.get("accepts", [])
            )
            if not has_task and not accepts_milestone:
                errors.append(f"{identifier}: TEST должен traces_to TASK либо accepts milestone")
            if not relations.get("verifies") and not any(
                str(target).lower().startswith("m") for target in relations.get("accepts", [])
            ):
                errors.append(
                    f"{identifier}: TEST должен verifies трассируемое свойство либо accepts milestone"
                )
    return _result("traceability", errors)


def check_full_traceability(root: Path) -> CheckResult:
    return _result("full_traceability", validate_full_traceability(root))


def check_semantic_consistency(root: Path) -> CheckResult:
    return _result("semantic_consistency", validate_semantic_consistency(root))


def check_authority_graph(root: Path) -> CheckResult:
    errors: list[str] = []
    for relative, doc in _primary_documents(root):
        deps = {value.strip().lower() for value in metadata_list(doc.metadata, "depends_on")}
        if str(doc.metadata.get("type", "")).strip() in {
            "system_specification",
            "security_specification",
        }:
            forbidden = {"architecture_baseline", "infrastructure_baseline"}.intersection(deps)
            if forbidden:
                errors.append(
                    f"{relative}: SYS/SEC specification не может depends_on нижний слой {sorted(forbidden)}"
                )

    docs = list(_primary_documents(root))
    by_id = {
        str(doc.metadata.get("id", "")).strip().lower(): relative
        for relative, doc in docs
        if str(doc.metadata.get("id", "")).strip()
    }
    graph: dict[str, set[str]] = {}
    for relative, doc in docs:
        identifier = str(doc.metadata.get("id", "")).strip().lower()
        if not identifier:
            continue
        deps = {
            value.strip().lower()
            for value in metadata_list(doc.metadata, "depends_on")
            if value.strip()
        }
        unknown = sorted(dep for dep in deps if dep not in by_id)
        for dep in unknown:
            errors.append(f"{relative}: depends_on ссылается на неизвестный document id {dep}")
        graph[identifier] = {dep for dep in deps if dep in by_id}

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, stack: list[str]) -> None:
        if node in visited:
            return
        if node in visiting:
            try:
                start = stack.index(node)
                cycle_nodes = stack[start:] + [node]
            except ValueError:
                cycle_nodes = stack + [node]
            errors.append("depends_on cycle: " + " -> ".join(cycle_nodes))
            return
        visiting.add(node)
        stack.append(node)
        for dep in sorted(graph.get(node, set())):
            visit(dep, stack)
        stack.pop()
        visiting.discard(node)
        visited.add(node)

    for node in sorted(graph):
        visit(node, [])

    try:
        milestones = collect_milestones(root)
    except Exception as exc:
        return _result("authority_graph", [str(exc)])
    m01 = next((item for item in milestones["items"] if str(item["id"]) == "m01"), None)
    if m01 and m01.get("scope"):
        errors.append(
            "m01: foundation milestone не должен объявлять product requirement implementation scope"
        )

    architecture_path = "specifications/architecture_baseline.md"
    architecture = read_text(root / architecture_path)
    if "Каноническое постоянное состояние принадлежит платформе" in architecture:
        errors.append(f"{architecture_path}: ownership данных противоречит Конституции")
    threat_path = "specifications/threat_model.md"
    threat = read_text(root / threat_path)
    if "platform-owned policy" in threat:
        errors.append(f"{threat_path}: policy не должна объявляться собственностью платформы")
    return _result("authority_graph", errors)


def check_document_policy(root: Path) -> CheckResult:
    errors: list[str] = []
    warnings: list[str] = []
    for path in iter_files(
        root,
        suffixes={".md", ".py", ".ps1", ".json", ".yaml", ".yml", ".toml"},
        include_generated=False,
    ):
        relative = relative_posix(path, root)
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if relative in STABLE_CONTENT_PATHS or relative.startswith("specifications/"):
            for pattern in STABLE_FORBIDDEN:
                match = pattern.search(text)
                if match:
                    errors.append(
                        f"{relative}: stable source содержит roadmap/implementation token '{match.group(0)}'"
                    )
        if relative != "operations/scripts/documents/check.py":
            for token in DEPRECATED_TOKENS:
                if token in text:
                    errors.append(f"{relative}: найден deprecated token '{token}'")
        if relative.endswith(".md"):
            for line_number, line in enumerate(text.splitlines(), start=1):
                match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
                if not match:
                    continue
                heading = match.group(1).lstrip("`*_ ")
                if heading and heading[0] in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя":
                    errors.append(
                        f"{relative}:{line_number}: русский заголовок должен начинаться с прописной буквы"
                    )
    misplaced_sections = {
        "specifications/architecture_baseline.md": "Граница с инфраструктурой",
        "specifications/infrastructure_baseline.md": "Граница с ADR и operations",
        "specifications/threat_model.md": "Когда модель угроз пересматривается",
    }
    expected_last_sections = {
        "specifications/architecture_baseline.md": "Стабильные архитектурные потоки",
        "specifications/infrastructure_baseline.md": "Инфраструктурные потоки",
        "specifications/threat_model.md": "Каталог угроз",
    }
    for relative, heading in misplaced_sections.items():
        text = read_text(root / relative)
        if re.search(rf"(?m)^##\s+(?:\d+\.\s*)?{re.escape(heading)}\s*$", text, re.IGNORECASE):
            errors.append(
                f"{relative}: процессный раздел '{heading}' должен находиться только в operations/change_process.md"
            )
        headings = re.findall(r"(?m)^##\s+(?:\d+\.\s*)?(.+?)\s*$", text)
        if not headings or headings[-1] != expected_last_sections[relative]:
            errors.append(
                f"{relative}: последний раздел должен оставаться предметным разделом "
                f"'{expected_last_sections[relative]}'; процессные правила принадлежат operations/change_process.md"
            )
    change_process = read_text(root / "operations/change_process.md")
    if not re.search(r"(?m)^##\s+7\.\s+Границы и пересмотр спецификаций\s*$", change_process):
        errors.append(
            "operations/change_process.md: отсутствует канонический раздел о границах и пересмотре спецификаций"
        )
    system_path = "specifications/system_specification.md"
    system_text = read_text(root / system_path)
    ordered_ids = re.findall(r"(?m)^###\s+((?:SYS|SEC_CTL)_\d{3})\s+—", system_text)
    expected_order = sorted(
        ordered_ids,
        key=lambda identifier: (
            0 if identifier.startswith("SYS_") else 1,
            int(identifier.rsplit("_", 1)[1]),
        ),
    )
    if ordered_ids != expected_order:
        errors.append(
            f"{system_path}: SYS и SEC_CTL должны быть расположены по порядку идентификаторов"
        )
    records = collect_traceable_elements(root)
    misplaced_requirements = sorted(
        identifier
        for identifier, record in records.items()
        if record["family"] in {"SYS", "SEC_CTL"} and record["path"] != system_path
    )
    if misplaced_requirements:
        errors.append(
            f"{system_path}: все SYS и SEC_CTL должны находиться в едином файле; "
            f"вне файла найдены {misplaced_requirements}"
        )
    return _result("document_policy", errors, warnings)


MILESTONE_HEADING_PATTERN = re.compile(r"(?m)^##\s+(m\d{2})\s+—\s+.+$", re.IGNORECASE)
BR_ID_PATTERN = re.compile(r"\bBR_\d{3}\b")
V1_SCOPE_LINE_PATTERN = re.compile(r"(?m)^Обязательный состав продукта:\s*(.+?)\s*$")
CANDIDATES_HEADING_PATTERN = re.compile(r"(?m)^#{2,3}\s+(?:\d+\.\s*)?Кандидатные направления.*$")
CANDIDATE_ROW_PATTERN = re.compile(r"(?m)^\|\s*\[`?(BR_\d{3})`?\]")
MILESTONE_SCOPE_LINE_PATTERN = re.compile(r"(?m)^-\s+состав:\s*(.+)$")
BR_PRIORITY_PATTERN = re.compile(
    r"(?ms)^###\s+(BR_\d{3})\s+—.*?^-\s+priority:\s*`([a-z]+)`\s*$",
)
CORE_PRIORITY = "core"


def _milestone_raw_sections(milestone_text: str) -> dict[str, str]:
    headings = list(MILESTONE_HEADING_PATTERN.finditer(milestone_text))
    raw_sections: dict[str, str] = {}
    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(milestone_text)
        raw_sections[match.group(1).lower()] = milestone_text[match.end() : end]
    return raw_sections


def _candidate_priorities(milestone_text: str) -> dict[str, str]:
    """Приоритет, продублированный в таблице кандидатов, по BR."""
    heading = CANDIDATES_HEADING_PATTERN.search(milestone_text)
    if not heading:
        return {}
    result: dict[str, str] = {}
    for line in milestone_text[heading.end() :].splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        identifier = CANDIDATE_ROW_PATTERN.search(line)
        priority = re.fullmatch(r"`([a-z]+)`", cells[2])
        if identifier and priority:
            result[identifier.group(1)] = priority.group(1)
    return result


def check_business_requirements_coverage(root: Path) -> CheckResult:
    """Каталог BR должен быть полностью и непересекающимся образом разложен на
    обязательный состав V1 и таблицу кандидатов после V1.

    Дополнительно проверяется смысл, а не только формальное разбиение:
    каждый BR приоритета `core` обязан входить в V1, каждый BR из состава V1
    обязан реально поставляться составом какого-то этапа внутри периметра V1,
    и продублированный в таблице кандидатов приоритет обязан совпадать с каталогом.
    Этапы после границы V1 планируют кандидатов легально и здесь не ограничиваются.
    """
    errors: list[str] = []
    br_text = read_text(root / "specifications" / "business_requirements.md")
    catalog = set(BR_ID_PATTERN.findall(br_text))
    if not catalog:
        return _result(
            "business_requirements_coverage",
            ["business_requirements.md: не найдено ни одного BR_*"],
        )
    priorities = {match.group(1): match.group(2) for match in BR_PRIORITY_PATTERN.finditer(br_text)}

    milestone_text = read_text(root / "milestones.md")
    v1_match = V1_SCOPE_LINE_PATTERN.search(milestone_text)
    # V1 scope is derived from core-priority requirements, not from explicit list
    # If explicit list exists, it must match core requirements
    if v1_match:
        v1_scope = BR_ID_PATTERN.findall(v1_match.group(1))
        v1_scope_set = set(v1_scope)
        if len(v1_scope) != len(v1_scope_set):
            errors.append("milestones.md: обязательный состав V1 содержит повторные BR_*")
    else:
        # No explicit list: derive V1 scope from core-priority requirements
        v1_scope_set = set()

    # If no explicit V1 scope list found, derive it from core-priority requirements
    if not v1_scope_set:
        v1_scope_set = {id for id in catalog if priorities.get(id) == CORE_PRIORITY}

    candidates_heading = CANDIDATES_HEADING_PATTERN.search(milestone_text)
    if not candidates_heading:
        errors.append(
            "milestones.md: не найден раздел 'Кандидатные направления' с таблицей BR после V1"
        )
    candidates_text = milestone_text[candidates_heading.end() :] if candidates_heading else ""
    candidates_set = set(CANDIDATE_ROW_PATTERN.findall(candidates_text))

    unknown_in_v1 = v1_scope_set - catalog
    unknown_in_candidates = candidates_set - catalog
    if unknown_in_v1:
        errors.append(
            f"milestones.md: состав V1 ссылается на неизвестные BR_*: {sorted(unknown_in_v1)}"
        )
    if unknown_in_candidates:
        errors.append(
            f"milestones.md: таблица кандидатов ссылается на неизвестные BR_*: {sorted(unknown_in_candidates)}"
        )

    overlap = v1_scope_set & candidates_set
    if overlap:
        errors.append(
            f"BR_* одновременно в составе V1 и в таблице кандидатов после V1: {sorted(overlap)}"
        )

    missing = catalog - (v1_scope_set | candidates_set)
    if missing:
        errors.append(
            f"BR_* не входит ни в состав V1, ни в таблицу кандидатов после V1: {sorted(missing)}"
        )

    # Периметр V1 выводится из приоритетов, а не задаётся вторым независимым решением:
    # состав обязан совпадать с множеством `core` в обе стороны, иначе появляются
    # два равноправных источника одного смысла.
    deferred_core = sorted(
        identifier for identifier in candidates_set if priorities.get(identifier) == CORE_PRIORITY
    )
    if deferred_core:
        errors.append(
            "BR_* с приоритетом `core` отложен за пределы V1: без него продукт теряет основной смысл, "
            f"поэтому он обязан входить в обязательный состав V1: {deferred_core}"
        )
    non_core_in_v1 = sorted(
        identifier
        for identifier in v1_scope_set
        if priorities.get(identifier, CORE_PRIORITY) != CORE_PRIORITY
    )
    if non_core_in_v1:
        errors.append(
            "BR_* без приоритета `core` включён в обязательный состав V1: периметр равен множеству `core`, "
            f"поэтому расширение выполняется изменением приоритета в каталоге: {non_core_in_v1}"
        )
    for identifier, declared in sorted(_candidate_priorities(milestone_text).items()):
        actual = priorities.get(identifier)
        if actual and actual != declared:
            errors.append(
                f"milestones.md: приоритет {identifier} в таблице кандидатов (`{declared}`) "
                f"разошёлся с каталогом business_requirements.md (`{actual}`)"
            )

    raw_sections = _milestone_raw_sections(milestone_text)
    v1_milestones = {value.lower() for value in v1_milestone_ids(root)}
    delivered_in_v1: set[str] = set()
    for milestone_id, section in raw_sections.items():
        if milestone_id not in v1_milestones:
            continue
        scope_line = MILESTONE_SCOPE_LINE_PATTERN.search(section)
        if scope_line:
            delivered_in_v1.update(BR_ID_PATTERN.findall(scope_line.group(1)))
    undelivered = v1_scope_set - delivered_in_v1
    unexpected_delivery = delivered_in_v1 & candidates_set
    if undelivered:
        errors.append(
            "BR_* заявлен в обязательном составе V1, но ни один этап внутри периметра V1 "
            f"не поставляет его через строку 'состав:': {sorted(undelivered)}"
        )
    if unexpected_delivery:
        errors.append(
            "BR_* из таблицы кандидатов после V1 поставляется этапом внутри периметра V1, "
            f"хотя не входит в обязательный состав V1: {sorted(unexpected_delivery)}"
        )
    return _result("business_requirements_coverage", errors)


def check_milestones(root: Path) -> CheckResult:
    errors: list[str] = []
    try:
        state = collect_milestones(root)
        records = collect_traceable_elements(root)
    except Exception as exc:
        return _result("milestones", [str(exc)])
    ids = [str(item["id"]) for item in state["items"]]
    expected = [f"m{index:02d}" for index in range(1, len(ids) + 1)]
    if ids != expected:
        errors.append(
            f"milestones должны идти последовательно: ожидалось {expected}, получено {ids}"
        )

    states = [str(item["work_state"]) for item in state["items"]]
    active_indexes = [
        index for index, value in enumerate(states) if value in {"in-progress", "blocked"}
    ]
    if len(active_indexes) > 1:
        errors.append("Одновременно может быть только один активный или заблокированный этап")
    first_unfinished = next(
        (index for index, value in enumerate(states) if value != "completed"), None
    )
    if (
        any(value == "completed" for value in states[(first_unfinished or 0) :])
        and first_unfinished is not None
    ):
        errors.append("Завершённые этапы должны образовывать непрерывный префикс без пропусков")
    if active_indexes and first_unfinished is not None and active_indexes[0] != first_unfinished:
        errors.append("Активным может быть только первый незавершённый этап")
    milestone_text = read_text(root / "milestones.md")
    raw_sections = _milestone_raw_sections(milestone_text)

    for item in state["items"]:
        for target in item.get("scope", []):
            if str(target) not in records:
                errors.append(f"{item['id']}: состав содержит неизвестный идентификатор {target}")
        if str(item.get("work_state")) in {"in-progress", "blocked"}:
            section = raw_sections.get(str(item["id"]).lower(), "")
            scope_line = re.search(r"(?m)^-\s+состав:\s*(.+)$", section)
            is_foundation = str(item["id"]).lower() == "m01"
            if not is_foundation and not item.get("scope"):
                errors.append(
                    f"{item['id']}: активный этап должен иметь непустой состав из точных идентификаторов"
                )
            if not is_foundation and not scope_line:
                errors.append(f"{item['id']}: активный этап должен содержать строку '- состав:'")
            if scope_line:
                raw_scope = scope_line.group(1).lower()
                if any(
                    token in raw_scope
                    for token in [
                        "*",
                        "применим",
                        "applicable",
                        "product scope",
                        "состав продукта",
                        "из раздела",
                    ]
                ):
                    errors.append(
                        f"{item['id']}: состав активного этапа должен быть выражен точными идентификаторами "
                        "без масок и ссылок на общий состав"
                    )
    return _result("milestones", errors)


def check_tasks(root: Path) -> CheckResult:
    errors: list[str] = []
    try:
        state = collect_tasks(root)
    except Exception as exc:
        return _result("tasks", [str(exc)])
    index_path = root / "tasks.md"
    if not index_path.exists():
        errors.append("Отсутствует tasks.md")
    elif render_task_index(root, "2000-01-01").strip() != read_text(index_path).strip():
        errors.append("tasks.md не соответствует карточкам TASK/TEST")
    required_headings = [
        "Зачем это делаем",
        "Результат",
        "Где мы сейчас",
        "Что делать сейчас",
        "План выполнения",
        "Состав",
        "Проверки и доказательства",
        "Готово когда",
        "Что будет дальше",
    ]
    for task in state["tasks"]:
        relative = str(task["path"])
        body = str(task["body"])
        actor = str(task["next_actor"])
        owner_action = str(task["owner_action"])
        allowed_paths = [str(value) for value in task.get("allowed_paths", [])]
        if actor not in {"owner", "agent", "automation", "none"}:
            errors.append(f"{relative}: неизвестный next_actor '{actor}'")
        if actor == "owner" and owner_action == "none":
            errors.append(f"{relative}: next_actor=owner требует одно конкретное owner_action")
        if actor != "owner" and owner_action != "none":
            errors.append(f"{relative}: owner_action задано, но next_actor не owner")
        if owner_action != "none" and owner_action not in body:
            errors.append(
                f"{relative}: owner_action должно дословно присутствовать в разделе владельца"
            )
        if str(task["work_state"]) in {"completed", "cancelled"} and actor != "none":
            errors.append(
                f"{relative}: завершённая или отменённая TASK должна иметь next_actor=none"
            )
        if str(task["work_state"]) == "completed":
            component = str(task.get("component", ""))
            placeholder_result = (
                f"Компонент `{component}` полностью реализован, протестирован и интегрирован."
            )
            if _markdown_section(body, "Результат") == placeholder_result:
                errors.append(
                    f"{relative}: раздел 'Результат' завершённой TASK не может оставаться "
                    "шаблонной заглушкой auto_generate_tasks.py — опишите, что реально "
                    "поставлено (конкретные модули, ограничения, что НЕ сделано)"
                )
            owner_capability = _markdown_section(body, "Что это даёт владельцу")
            if not owner_capability:
                errors.append(
                    f"{relative}: завершённая TASK должна содержать раздел "
                    "'Что это даёт владельцу' — 1-3 предложения на бытовом языке о новой "
                    "возможности для владельца"
                )
            elif owner_capability == "Функционал появится после завершения этой TASK.":
                errors.append(
                    f"{relative}: раздел 'Что это даёт владельцу' завершённой TASK не может "
                    "оставаться шаблонной заглушкой auto_generate_tasks.py"
                )
        if str(task["work_state"]) in {"planned", "in-progress", "blocked"} and actor == "none":
            errors.append(
                f"{relative}: незавершённая TASK должна иметь одного следующего исполнителя"
            )
        actor_heading = {"owner": "Владельцу", "agent": "Агенту", "automation": "Автоматике"}.get(
            actor
        )
        if actor_heading and not re.search(rf"(?m)^###\s+{actor_heading}\s*$", body):
            errors.append(f"{relative}: next_actor={actor} требует раздел '{actor_heading}'")
        if not task["checklist"]:
            errors.append(f"{relative}: раздел 'План выполнения' должен содержать checklist")
        if str(task["work_state"]) == "completed" and int(task["steps_remaining"]) != 0:
            errors.append(f"{relative}: completed TASK не может содержать невыполненные шаги")
        if owner_action == "none":
            if re.search(
                r"(?m)^###\s+Владельцу\s*$|^##\s+(?:\d+\.\s*)?Пошаговая инструкция владельцу\s*$",
                body,
            ):
                errors.append(
                    f"{relative}: пустой раздел владельца запрещён, когда owner_action=none"
                )
        elif not re.search(r"(?m)^###\s+Владельцу\s*$", body):
            errors.append(f"{relative}: для owner_action нужен раздел 'Владельцу'")
        if "%" in body:
            errors.append(
                f"{relative}: искусственные проценты запрещены; используйте checklist и счётчики"
            )
        if not allowed_paths:
            errors.append(f"{relative}: TASK должна содержать непустой список allowed_paths")
        if relative not in allowed_paths:
            errors.append(f"{relative}: allowed_paths должен включать собственный файл TASK")
        if str(task["work_state"]) == "blocked" and not str(task.get("blocker", "")).strip():
            errors.append(f"{relative}: заблокированная TASK должна указывать причину в blocker")
        if str(task["work_state"]) != "blocked" and str(task.get("blocker", "")).strip():
            errors.append(f"{relative}: blocker допустим только при work_state=blocked")
        open_followup_actions: list[str] = []
        for followup in task.get("owner_followups", []):
            status = str(followup.get("status", ""))
            action = str(followup.get("action", ""))
            if status not in {"open", "done"}:
                errors.append(
                    f"{relative}: owner_followups: status должен быть 'open' или 'done', "
                    f"получено '{status}'"
                )
            if not action:
                errors.append(f"{relative}: owner_followups: action не может быть пустым")
            elif status == "open":
                open_followup_actions.append(action)
                if action not in body:
                    errors.append(
                        f"{relative}: owner_followups: открытое действие должно дословно "
                        "присутствовать в разделе 'Незакрытые действия владельца'"
                    )
        has_followups_heading = bool(
            re.search(
                r"(?m)^##\s+(?:\d+\.\s*)?Незакрытые действия владельца\s*$",
                body,
            )
        )
        if open_followup_actions and not has_followups_heading:
            errors.append(
                f"{relative}: есть открытые owner_followups, но нет раздела "
                "'Незакрытые действия владельца'"
            )
        if has_followups_heading and not open_followup_actions:
            errors.append(
                f"{relative}: раздел 'Незакрытые действия владельца' присутствует, "
                "но нет ни одного открытого owner_followups"
            )
        for heading in required_headings:
            if not re.search(
                rf"^##\s+(?:\d+\.\s*)?{re.escape(heading)}\b", body, re.MULTILINE | re.IGNORECASE
            ):
                errors.append(f"{relative}: отсутствует раздел '{heading}'")
    return _result("tasks", errors)


def _markdown_section(body: str, heading: str) -> str:
    match = re.search(
        rf"(?ms)^##\s+(?:\d+\.\s*)?{re.escape(heading)}\s*$\n(.*?)(?=^##\s|\Z)",
        body,
    )
    return match.group(1).strip() if match else ""


def check_test_specs(root: Path) -> CheckResult:
    errors: list[str] = []
    records = collect_traceable_elements(root)
    milestone_ids = {str(item["id"]).lower() for item in collect_milestones(root)["items"]}
    try:
        raw_catalog = load_quality_registry(root).get("evidence_catalog", {})
        evidence_ids = (
            {str(value) for value in raw_catalog} if isinstance(raw_catalog, dict) else set()
        )
    except Exception:
        evidence_ids = set()
    tests_dir = root / "work/tests"
    seen: set[str] = set()
    for path in sorted(tests_dir.glob("*.md")):
        relative = relative_posix(path, root)
        if not TEST_FILE_PATTERN.fullmatch(path.name):
            errors.append(f"Некорректное имя проверки: {relative}")
            continue
        doc = load_document(path)
        identifier = str(doc.metadata.get("id", "")).strip()
        if not TEST_ID_PATTERN.fullmatch(identifier):
            errors.append(f"{relative}: id должен иметь формат TEST_001")
        if identifier in seen:
            errors.append(f"Дублирующий TEST id: {identifier}")
        seen.add(identifier)
        spec_state = str(doc.metadata.get("spec_state", "")).strip().lower()
        if spec_state not in STATE_VALUES["spec_state"]:
            errors.append(f"{relative}: неизвестный spec_state '{spec_state}'")
        traces = [value.strip() for value in metadata_list(doc.metadata, "traces_to")]
        verifies = [value.strip() for value in metadata_list(doc.metadata, "verifies")]
        accepts = [value.strip().lower() for value in metadata_list(doc.metadata, "accepts")]
        execution = str(doc.metadata.get("execution", "")).strip().lower()
        automated_evidence = str(doc.metadata.get("automated_evidence", "")).strip()
        manual_evidence = str(doc.metadata.get("manual_evidence", "")).strip()
        if not any(TASK_ID_PATTERN.fullmatch(value) for value in traces) and not accepts:
            errors.append(f"{relative}: нужен traces_to на TASK_xxxx либо accepts на этап")
        if not verifies and not any(
            re.fullmatch(r"m\d{2}", value, re.IGNORECASE) for value in accepts
        ):
            errors.append(
                f"{relative}: нужен verifies трассируемого свойства либо accepts milestone"
            )
        if execution not in TEST_EXECUTIONS:
            errors.append(f"{relative}: execution должен быть automated или manual")
        if execution == "automated":
            if not automated_evidence:
                errors.append(f"{relative}: automated TEST должен иметь automated_evidence")
            if manual_evidence:
                errors.append(f"{relative}: automated TEST не должен иметь manual_evidence")
            if not re.search(
                r"^##\s+(?:\d+\.\s*)?Автоматический запуск\b",
                doc.body,
                re.MULTILINE | re.IGNORECASE,
            ):
                errors.append(
                    f"{relative}: automated TEST должен содержать раздел 'Автоматический запуск'"
                )
            if re.search(
                r"(?mi)^##\s+(?:\d+\.\s*)?(?:Пошаговая инструкция|Действия владельца)\b|^###\s+Владельцу\s*$",
                doc.body,
            ):
                errors.append(
                    f"{relative}: automated TEST не должен содержать инструкции владельцу"
                )
            if automated_evidence and automated_evidence not in evidence_ids:
                errors.append(f"{relative}: неизвестный automated_evidence '{automated_evidence}'")
        if execution == "manual":
            if automated_evidence:
                errors.append(f"{relative}: manual TEST не должен иметь automated_evidence")
            if not manual_evidence:
                errors.append(f"{relative}: manual TEST должен иметь manual_evidence")
            if manual_evidence and manual_evidence not in evidence_ids:
                errors.append(f"{relative}: неизвестный manual_evidence '{manual_evidence}'")
            owner_steps = _markdown_section(doc.body, "Действия владельца")
            if not owner_steps:
                errors.append(
                    f"{relative}: manual TEST должен содержать раздел 'Действия владельца'"
                )
            unsafe = re.search(
                r"(?i)\b(?:git|powershell|pwsh)\b|operations[\\/]scripts|\.ps1\b", owner_steps
            )
            if unsafe:
                errors.append(
                    f"{relative}: manual TEST не может требовать от владельца Git, PowerShell или внутренние скрипты"
                )
        for target in verifies:
            if target not in records:
                errors.append(
                    f"{relative}: verifies ссылается на неизвестный трассируемый id '{target}'"
                )
        for milestone in accepts:
            if milestone not in milestone_ids:
                errors.append(
                    f"{relative}: accepts ссылается на неизвестный milestone '{milestone}'"
                )
        for required_heading in [
            "Назначение",
            "Что проверяется",
            "Критерий успеха",
            "Состав доказательства",
        ]:
            if not re.search(
                rf"^##\s+(?:\d+\.\s+)?{re.escape(required_heading)}\b",
                doc.body,
                re.MULTILINE | re.IGNORECASE,
            ):
                errors.append(f"{relative}: отсутствует раздел '{required_heading}'")
    return _result("test_specs", errors)


def check_quality_registry(root: Path) -> CheckResult:
    try:
        milestone_ids = {str(item["id"]).lower() for item in collect_milestones(root)["items"]}
    except Exception as exc:
        return _result("quality_registry", [str(exc)])
    return _result("quality_registry", validate_quality_registry(root, milestone_ids))


def check_acceptance_model(root: Path) -> CheckResult:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        milestones = collect_milestones(root)
        collect_tasks(root)
        collect_test_specs(root)
        registry = load_quality_registry(root)
    except Exception as exc:
        return _result("acceptance_model", [str(exc)])

    current = milestones["current"]
    current_id = str(current["id"])
    current_work_state = str(current.get("work_state", "planned"))
    profiles = profiles_for_milestone(registry, current_id)
    if not profiles:
        if current_work_state == "planned":
            warnings.append(
                f"{current_id}: quality profile станет обязательным при переводе milestone в in-progress"
            )
            return _result("acceptance_model", errors, warnings)
        errors.append(f"Для активного milestone {current_id} отсутствует quality profile")
        return _result("acceptance_model", errors, warnings)

    modes = {str(raw.get("scope_coverage", "task_test")) for _, raw in profiles}

    if "global_evidence" in modes:
        for profile_id, raw in profiles:
            if str(raw.get("scope_coverage", "task_test")) == "global_evidence" and not raw.get(
                "scope_evidence"
            ):
                errors.append(f"{profile_id}: global_evidence без scope_evidence")
    else:
        errors.extend(validate_task_semantics(root, current_id))
    return _result("acceptance_model", errors, warnings)


def _block_scalar_errors(workflow_name: str, text: str) -> list[str]:
    """Найти строки многострочного скрипта, выпавшие из блока YAML.

    Многострочный `run: |` рвётся, если продолжение оказывается на отступе
    не глубже самого ключа: YAML молча закрывает блок, и рабочий процесс
    перестаёт разбираться. Полноценный разбор YAML сюда не тянется, чтобы
    не заводить внешнюю зависимость ради одного правила.
    """
    errors: list[str] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        opening = re.match(r"^(\s*)-?\s*(?:run|if|shell):\s*[|>][+-]?\s*$", line)
        if not opening:
            continue
        key_indent = len(opening.group(1))
        for offset, following in enumerate(lines[index + 1 :], start=index + 2):
            if not following.strip():
                continue
            indent = len(following) - len(following.lstrip())
            if indent > key_indent:
                continue
            if re.match(r"^\s*(?:-\s|\w[\w-]*:)", following):
                break
            errors.append(
                f"{workflow_name}:{offset}: строка многострочного блока не глубже ключа "
                f"и разрывает его: {following.strip()[:60]}"
            )
            break
    return errors


def check_automation_policy(root: Path) -> CheckResult:
    errors: list[str] = []
    project_workflow = read_text(root / ".github/workflows/project_check.yml")
    acceptance = read_text(root / "operations/scripts/acceptance/apply.py")

    if not re.search(r"(?ms)^permissions:\s*\n\s+contents:\s*read\s*$", project_workflow):
        errors.append("project_check.yml должен иметь contents: read")
    if re.search(r"(?ms)^\s*pull_request:\s*\n\s+paths(?:-ignore)?:", project_workflow):
        errors.append(
            "Project check должен запускаться на каждом PR без path-filter, чтобы новые типы файлов не обходили проверки"
        )
    if "operations\\scripts\\tasks\\check_change_scope.py" not in project_workflow:
        errors.append("Project check должен проверять покрытие изменённых путей TASK")
    if "runs-on: ubuntu-latest" not in project_workflow:
        errors.append("Project check должен содержать переносимую проверку Python на Linux")
    push_trigger = re.search(
        r"(?m)^  push:\s*$\n(?P<body>(?:[ \t]+[^\n]*\n)*)",
        project_workflow,
    )
    if not push_trigger or not re.search(r"(?m)^\s+-\s+main\s*$", push_trigger.group("body")):
        errors.append(
            "Project check должен запускаться по push на main: любое прямое изменение main должно "
            "пройти те же проверки, что и запрос на слияние (см. operations/change_process.md)"
        )
    elif re.search(r"(?m)^\s+paths(?:-ignore)?:\s*$", push_trigger.group("body")):
        errors.append(
            "Триггер push на main не может иметь path-filter: отфильтрованный триггер молча перестаёт "
            "срабатывать"
        )
    if "commits/$env:GITHUB_SHA/pulls" not in project_workflow:
        errors.append(
            "Project check должен обнаруживать push в main без связанного merged pull request"
        )
    workflow_paths = sorted((root / ".github/workflows").glob("*.yml")) + sorted(
        (root / ".github/workflows").glob("*.yaml")
    )
    for workflow_path in workflow_paths:
        workflow_name = workflow_path.name
        workflow_text = read_text(workflow_path)
        errors.extend(_block_scalar_errors(workflow_name, workflow_text))
        permission_match = re.search(
            r"(?m)^permissions:\s*$\n(?P<body>(?:[ \t]+[^\n]*\n)*)",
            workflow_text,
        )
        permission_body = permission_match.group("body") if permission_match else ""
        if not re.search(r"(?m)^[ \t]+contents:\s*read\s*$", permission_body):
            errors.append(
                f"{workflow_name}: persistent workflow должен явно ограничивать repository permission до contents: read"
            )
        if "contents: write" in workflow_text.lower():
            errors.append(f"{workflow_name}: persistent workflow не может иметь contents: write")
        # Штатная автоматизация остаётся читающей целиком, а не только по contents.
        # Иначе полномочия расширяются молча, добавлением одной строки в permissions.
        for scope, value in re.findall(r"(?m)^[ \t]+([a-z-]+):\s*([a-z]+)\s*$", permission_body):
            if value not in ALLOWED_WORKFLOW_PERMISSIONS:
                errors.append(
                    f"{workflow_name}: разрешение '{scope}: {value}' расширяет полномочия автоматизации; "
                    f"допустимы только {sorted(ALLOWED_WORKFLOW_PERMISSIONS)} (operations/change_process.md, раздел 5)"
                )
        for token in ["git push", "git commit"]:
            if token in workflow_text.lower():
                errors.append(
                    f"{workflow_name}: persistent workflow содержит repository mutation primitive {token}"
                )
        for match in re.finditer(r"(?m)^\s*uses:\s*([^@\s#]+)@([^\s#]+)", workflow_text):
            action, ref = match.groups()
            if action.startswith("./") or action.startswith("docker://"):
                continue
            if not re.fullmatch(r"[0-9a-fA-F]{40}", ref):
                errors.append(
                    f"{workflow_name}: external Action {action}@{ref} должен быть pinned на immutable 40-char commit SHA"
                )
    for token in ["git push", "git commit"]:
        if token in acceptance.lower():
            errors.append(f"acceptance/apply.py не должен выполнять {token}")
    if "--semantic-review" not in acceptance or "validate_semantic_review" not in acceptance:
        errors.append("acceptance/apply.py должен требовать SHA-bound semantic review для m01")
    return _result("automation_policy", errors)


def check_generated(root: Path) -> CheckResult:
    errors: list[str] = []
    required = [
        root / "project_status.md",
        root / "tasks.md",
        root / "generated/markdown_index.md",
        root / "generated/non_markdown_index.md",
        root / "generated/repository_structure.md",
        root / "generated/traceability_matrix.md",
        root / "generated/test_catalog.md",
        root / "generated/platfrom_capability.md",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"Отсутствует производный файл: {relative_posix(path, root)}")
            continue
        first = path.read_text(encoding="utf-8-sig").splitlines()[0:1]
        if first != [GENERATED_HEADER]:
            errors.append(f"{relative_posix(path, root)}: отсутствует marker generated")
    expected = {
        root / "project_status.md": render_repository_project_status(root),
        root / "tasks.md": render_task_index(root, "2000-01-01"),
        root / "generated/markdown_index.md": render_index(root, "2000-01-01"),
        root / "generated/non_markdown_index.md": render_non_markdown_index(root, "2000-01-01"),
        root / "generated/repository_structure.md": render_repository_structure(root, "2000-01-01"),
        root / "generated/traceability_matrix.md": render_traceability(root, "2000-01-01"),
        root / "generated/test_catalog.md": render_test_catalog(root, "2000-01-01"),
        root / "generated/platfrom_capability.md": render_platfrom_capability(root, "2000-01-01"),
    }
    for path, rendered in expected.items():
        if path.exists() and not generated_content_matches(read_text(path), rendered):
            errors.append(f"{relative_posix(path, root)} не соответствует генератору")
    return _result("generated", errors)


def check_owner_interface(root: Path) -> CheckResult:
    errors: list[str] = []
    rendered = render_repository_project_status(root)
    if "%" in rendered:
        errors.append("project_status.md не должен содержать искусственные проценты")
    for token in [
        "[x]",
        "[ ]",
        "выполнено",
        "осталось",
        "Ваше действие сейчас",
        "Следующий исполнитель",
        "Блокеры",
    ]:
        if token not in rendered:
            errors.append(f"project_status.md: отсутствует обязательный элемент '{token}'")
    if not any(
        phrase in rendered
        for phrase in [
            "Чтобы продолжить, отправьте агенту одну команду",
            "Чтобы продолжить, откройте новый сеанс агента",
            "Сейчас требуется ваше решение",
        ]
    ):
        errors.append("project_status.md должен явно сообщать, требуется ли действие владельца")
    for token in [
        "in-review",
        "in-progress",
        "ready-for-acceptance",
        "owner_action",
        "PowerShell",
        "Git SHA",
        "evidence bundle",
    ]:
        if token in rendered:
            errors.append(
                f"project_status.md: внутренняя техническая деталь '{token}' не должна показываться владельцу"
            )
    if rendered.count("| Следующий исполнитель |") != 1:
        errors.append("project_status.md должен показывать ровно одного следующего исполнителя")
    return _result("owner_interface", errors)


def check_secrets(root: Path) -> CheckResult:
    errors: list[str] = []
    forbidden_names = {".env", "id_rsa", "id_ed25519", "credentials.json"}
    # Производные представления тоже сканируются: секрет, попавший в первичный документ,
    # копируется в generated/ и обязан обнаруживаться там же.
    for path in iter_files(root, include_generated=True):
        relative = relative_posix(path, root)
        if path.name.lower() in forbidden_names or path.suffix.lower() in {".pem", ".p12", ".pfx"}:
            errors.append(f"Потенциальный секрет: {relative}")
            continue
        if path.suffix.lower() not in SCANNED_TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            errors.append(f"{relative}: найден фрагмент, похожий на секрет")
    return _result("secrets", errors)


def check_test_coverage_quality(root: Path) -> CheckResult:
    """Проверка покрытия требований тестами (включается на m02+)."""
    # На m01 только подготовка основы, требования будут протестированы на m02+
    # Эта проверка информационная и не блокирует принятие m01
    try:
        from operations.scripts.quality.test_coverage import validate_test_coverage

        return _result("test_coverage", validate_test_coverage(root))
    except Exception as exc:
        return _result("test_coverage", [f"Ошибка проверки: {exc}"])


def check_owner_action_quality(root: Path) -> CheckResult:
    """Проверка практичности действий владельца."""
    try:
        from operations.scripts.quality.action_practicality import check_project_status

        errors = check_project_status(root)
        return _result("owner_actions", errors if errors else [])
    except Exception as exc:
        return _result("owner_actions", [f"Ошибка проверки: {exc}"])


def check_allowed_paths_quality(root: Path) -> CheckResult:
    """Проверка консистентности путей в allowed_paths."""
    try:
        from operations.scripts.quality.paths_validation import validate_task_paths

        errors = validate_task_paths(root)
        return _result("allowed_paths", errors if errors else [])
    except Exception as exc:
        return _result("allowed_paths", [f"Ошибка проверки: {exc}"])


def check_frontmatter_standard(root: Path) -> CheckResult:
    """Проверка соответствия frontmatter стандарту по типам документов.

    Согласно operations/change_process.md#82, каждый тип документа
    должен иметь определённый минимальный набор полей.
    """
    errors: list[str] = []

    # Минимальные требуемые поля по типам документов
    type_requirements = {
        "adr": {"id", "type", "decision_state", "version", "updated", "traces_to"},
        "task": {
            "id",
            "type",
            "title",
            "work_state",
            "version",
            "updated",
            "depends_on",
            "next_actor",
            "owner_action",
            "allowed_paths",
            "traces_to",
        },
        "test": {"id", "type", "spec_state", "version", "updated"},
        "quality_evidence": {"id", "type", "evidence_state", "version", "created"},
        "generated_owner_status": {"id", "type", "generation_state", "version"},
        # Первичные документы (правила, спецификации и т.п.)
        "project_rules": {"id", "type", "document_state", "version", "updated", "depends_on"},
        "business_requirements": {
            "id",
            "type",
            "document_state",
            "version",
            "updated",
            "depends_on",
        },
        "system_specification": {
            "id",
            "type",
            "document_state",
            "version",
            "updated",
            "depends_on",
        },
        "threat_model": {"id", "type", "document_state", "version", "updated", "depends_on"},
        "architecture_baseline": {
            "id",
            "type",
            "document_state",
            "version",
            "updated",
            "depends_on",
        },
        "infrastructure_baseline": {
            "id",
            "type",
            "document_state",
            "version",
            "updated",
            "depends_on",
        },
        "agent_instruction": {"id", "type", "document_state", "version", "updated", "depends_on"},
        "operations": {"id", "type", "document_state", "version", "updated", "depends_on"},
        "checklist": {"id", "type", "document_state", "version", "updated", "depends_on"},
    }

    for relative, doc in _primary_documents(root):
        doc_type = str(doc.metadata.get("type", "")).strip()
        if not doc_type:
            continue

        # Пропускаем шаблоны и генерируемые файлы
        if relative.startswith("operations/templates/") or "generated" in relative:
            continue

        required = type_requirements.get(doc_type)
        if not required:
            # Для неизвестных типов не проверяем
            continue

        # Проверяем наличие требуемых полей
        missing = required - set(doc.metadata.keys())
        if missing:
            errors.append(
                f"{relative}: для типа '{doc_type}' отсутствуют поля: {', '.join(sorted(missing))}"
            )

        # Проверяем специфические требования
        if doc_type == "task":
            next_actor = str(doc.metadata.get("next_actor", "")).strip()
            if next_actor == "owner":
                owner_action = str(doc.metadata.get("owner_action", "")).strip()
                if owner_action == "none":
                    errors.append(
                        f"{relative}: при next_actor=owner, owner_action не должен быть 'none'"
                    )

            # Проверяем, что allowed_paths имеет значения
            paths = doc.metadata.get("allowed_paths", [])
            if not paths or (isinstance(paths, list) and not any(paths)):
                errors.append(f"{relative}: allowed_paths должен содержать хотя бы один путь")

        if doc_type == "test":
            execution = str(doc.metadata.get("execution", "owner")).strip().lower() or "owner"
            if execution == "automated":
                evidence = doc.metadata.get("automated_evidence", "")
                if not evidence or str(evidence).strip() == "":
                    errors.append(
                        f"{relative}: при execution=automated, должно быть заполнено automated_evidence"
                    )
            elif execution == "manual":
                evidence = doc.metadata.get("manual_evidence", "")
                if not evidence or str(evidence).strip() == "":
                    errors.append(
                        f"{relative}: при execution=manual, должно быть заполнено manual_evidence"
                    )

    return _result("frontmatter_standard", errors)


def run_all_checks(root: Path, fast: bool = False) -> list[CheckResult]:
    # Fast mode: только быстрые структурные проверки (<0.2s каждая)
    fast_checks = [
        ("structure", check_structure),
        ("metadata", check_metadata),
        ("frontmatter_standard", check_frontmatter_standard),
        ("links", lambda project_root: _result("links", check_markdown_links(project_root))),
        ("secrets", check_secrets),
    ]
    # Full mode: все проверки (для CI)
    all_checks = [
        ("structure", check_structure),
        ("metadata", check_metadata),
        ("frontmatter_standard", check_frontmatter_standard),
        ("traceability", check_traceability),
        ("full_traceability", check_full_traceability),
        ("semantic_consistency", check_semantic_consistency),
        ("authority_graph", check_authority_graph),
        ("document_policy", check_document_policy),
        ("milestones", check_milestones),
        ("business_requirements_coverage", check_business_requirements_coverage),
        ("tasks", check_tasks),
        ("test_specs", check_test_specs),
        ("quality_registry", check_quality_registry),
        ("acceptance_model", check_acceptance_model),
        ("automation_policy", check_automation_policy),
        ("links", lambda project_root: _result("links", check_markdown_links(project_root))),
        ("generated", check_generated),
        ("owner_interface", check_owner_interface),
        ("secrets", check_secrets),
        ("test_coverage", check_test_coverage_quality),
        ("owner_actions", check_owner_action_quality),
        ("allowed_paths", check_allowed_paths_quality),
    ]
    checks = fast_checks if fast else all_checks
    results: list[CheckResult] = []
    for name, checker in checks:
        try:
            results.append(checker(root))
        except Exception as exc:
            results.append(
                _result(name, [f"Непредвиденная ошибка проверки: {type(exc).__name__}: {exc}"])
            )
    return results


class CheckResultDict(TypedDict):
    name: str
    ok: bool
    errors: list[str]
    warnings: list[str]


class Summary(TypedDict):
    ok: bool
    checks: list[CheckResultDict]
    error_count: int
    warning_count: int


def summarize(results: list[CheckResult]) -> Summary:
    return {
        "ok": all(result.ok for result in results),
        "checks": [
            {
                "name": result.name,
                "ok": result.ok,
                "errors": result.errors,
                "warnings": result.warnings,
            }
            for result in results
        ],
        "error_count": sum(len(result.errors) for result in results),
        "warning_count": sum(len(result.warnings) for result in results),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверка personal_ai_platform")
    parser.add_argument("--all", action="store_true", help="Выполнить все проверки (по умолчанию)")
    parser.add_argument(
        "--fast", action="store_true", help="Выполнить только быстрые структурные проверки"
    )
    parser.add_argument("--json", action="store_true", help="Вывести результат в JSON")
    args = parser.parse_args()
    require_supported_python()
    root = find_project_root(Path.cwd())
    fast = args.fast and not args.all
    summary = summarize(run_all_checks(root, fast=fast))
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        for result in summary["checks"]:
            print(f"[{'PASS' if result['ok'] else 'FAIL'}] {result['name']}")
            for warning in result["warnings"]:
                print(f"  WARNING: {warning}")
            for error in result["errors"]:
                print(f"  ERROR: {error}")
        print(f"Итог: errors={summary['error_count']}, warnings={summary['warning_count']}")
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
