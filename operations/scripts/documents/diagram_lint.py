"""Проверка SVG-схем (архитектурных и процессных) на соответствие
operations/architecture/diagram_geometry_foundations.md и предметным гайдам
(architecture_diagram_style_guide.md, process_diagram_style_guide.md).

Вызывается из check.py --all автоматически (см.
diagram_geometry_foundations.md §13). Проверяет только то, что можно
проверить без рендеринга SVG: блок метаданных, дрейф заявленной версии
источника от фактической, наличие каждого заявленного ID в спецификации,
взаимное соответствие списка ID и data-spec-id в теле файла, полноту
семейств ID в легенде, привязку внешних подписей потоков, наследование
цвета прямого коннектора от его источника и базовую структуру
(viewBox/title/desc). Через diagram_geometry_lint дополнительно проверяет
дисциплину половинных координат, единый размер наконечника стрелки,
геометрически вычисленные вертикальные зазоры между связанными карточками,
прямолинейность и непересечение карточек общими трассами, а также равенство
геометрии однотипных контрольных переходов.

Не проверяет: контраст, реальное визуальное наложение текста, читаемость
после масштабирования, буквальную кратность 4 px для каждой координаты,
несвязанные `layer-gap`/`right-port-gap`/`right-rail-gap` — это остаётся
ручными пунктами чек-листа (diagram_geometry_foundations.md §17), поскольку
требует либо измеренного рендеринга текста, либо разрешения произвольного
стека `transform` (поворот, масштаб), которое нельзя сделать корректно без
риска ложных срабатываний.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, TypeVar

from defusedxml import ElementTree  # type: ignore[import-untyped]  # no PEP 561 marker
from defusedxml.common import DefusedXmlException  # type: ignore[import-untyped]  # same package

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import (
    find_project_root,
    read_text,
    relative_posix,
    require_supported_python,
)
from operations.scripts.documents.diagram_geometry_lint import (
    ControlTransitionLayout,
    FlowLabelLayout,
    check_geometry,
    measure_reference_card_text_inset,
    measure_reference_flow_caption_padding,
)
from operations.scripts.documents.metadata import load_document
from operations.scripts.documents.traceability import _normalize_id, collect_traceable_elements

_SVG_NS = "{http://www.w3.org/2000/svg}"

ARCHITECTURE_TEMPLATE_RELATIVE = Path(
    "operations/architecture/templates/architecture_diagram_template.svg"
)

_METADATA_BLOCK = re.compile(
    r"<!--\s*diagram-metadata\s*(?P<body>.*?)\s*end-diagram-metadata\s*-->",
    re.DOTALL,
)
_DATA_SPEC_ID = re.compile(r'data-spec-id="([^"]+)"')
_SOURCE_LINE = re.compile(r"^(?P<path>[^@\s]+)@(?P<version>\S+)$")
_REQUIRED_SCALAR_KEYS = ("diagram_id", "diagram_version", "generated_at", "status")
_VALID_STATUS = {"current", "superseded"}
_VISIBLE_META = re.compile(
    r'data-diagram-meta="version"[^>]*>(?P<text>[^<]*)<',
)
_VERSION_TOKEN = re.compile(r"\d+\.\d+")
_DATE_TOKEN = re.compile(r"\d{4}-\d{2}-\d{2}")
# No \b anchors: an ISO timestamp's "T17:20:00" has a word character (the
# "T") immediately before the hour digits, so \b would never match there --
# it only matches a transition between \w and \W. The narrow, controlled
# inputs this pattern searches (a generated_at scalar, a short header
# caption) carry no other colon-separated digit pairs to false-positive on.
_TIME_TOKEN = re.compile(r"(?P<hour>\d{2}):(?P<minute>\d{2})")
_STYLE_BLOCK = re.compile(r"<style[^>]*>(?P<body>.*?)</style>", re.DOTALL)
_CLASS_RULE = re.compile(
    r"(?:^|[,{}])\s*\.(?P<name>[A-Za-z_][A-Za-z0-9_-]*)\s*(?=[,{])", re.MULTILINE
)
_MARKER_ID = re.compile(r"<marker\b[^>]*\bid=\"(?P<name>[^\"]+)\"")
_URL_REF = re.compile(r"url\(#(?P<name>[^)]+)\)")
_ID_FAMILY = re.compile(r"^(?P<family>[A-Z]+(?:_[A-Z]+)*)_\d+$")
_LEGEND_FAMILY = re.compile(r"^(?P<family>[A-Z]+(?:_[A-Z]+)*)_\*$")
_VISIBLE_FLOW_ID = re.compile(r"\b(?:ARC_FLOW|INF_FLOW|SEC_CTL)_\d{3}\b")
_VISIBLE_ARC_FLOW_ID = re.compile(r"\bARC_FLOW_(?:\d{3}|XXX)\b")
_ID_SLASH_SEPARATOR = re.compile(
    r"\b(?:ARC_(?:CMP|FLOW)|INF_(?:CMP|FLOW)|SEC_CTL)_(?:\d{3}|XXX)(?:–\d{3})?"
    r"\s*/\s*(?:ARC_(?:CMP|FLOW)|INF_(?:CMP|FLOW)|SEC_CTL)_"
)
_ARCHITECTURE_ID_PREFIXES = ("ARC_", "INF_", "SEC_CTL_")

_SOURCE_PALETTE_CLASSES = {
    "blue": {"execution-card", "flow-label-blue"},
    "red": {"control-card", "flow-label-red"},
    "green": {"data-card", "flow-label-green"},
    "gray": {"neutral-card", "inner-card", "implementation-pill", "flow-label-gray"},
}
_CONNECTOR_PALETTE_CLASSES = {
    "blue": {"main-line", "merge-line", "branch-line", "bus-line", "scheduled-line"},
    "red": {
        "control-line",
        "control-rail",
        "control-main-line",
        "failure-line",
        "failure-bus",
        "revision-line",
    },
    "green": {"data-line", "data-merge-line"},
    "gray": {
        "neutral-line",
        "neutral-scheduled-line",
        "support-line",
        "support-rail",
        "implementation-link",
    },
}
_DIRECT_CONNECTOR_CLASSES = {
    "bus-line",
    "main-line",
    "merge-line",
    "neutral-line",
    "data-line",
    "data-merge-line",
    "control-main-line",
    "branch-line",
    "scheduled-line",
    "neutral-scheduled-line",
    "control-line",
    "failure-line",
    "revision-line",
}

_ARC_FLOW_FILL_CLASSES = {
    "control-card",
    "data-card",
    "execution-card",
    "flow-label-blue",
    "flow-label-gray",
    "flow-label-green",
    "flow-label-red",
    "inner-card",
    "neutral-card",
}
_FLOW_LABEL_PALETTE_CLASSES = {
    "blue": {"flow-label", "flow-label-blue"},
    "red": {"flow-label-red"},
    "green": {"flow-label-green"},
    "gray": {"flow-label-gray"},
}
_FLOW_LABEL_CLASSES = set().union(*_FLOW_LABEL_PALETTE_CLASSES.values())


@dataclass
class LintResult:
    file: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class _ParsedMetadata:
    scalars: dict[str, str]
    sources: list[str]
    ids: list[str]


def _parse_metadata_block(text: str, result: LintResult) -> _ParsedMetadata | None:
    match = _METADATA_BLOCK.search(text)
    if match is None:
        result.errors.append(
            "не найден обязательный блок метаданных "
            "(<!-- diagram-metadata ... end-diagram-metadata -->), "
            "см. diagram_geometry_foundations.md §13"
        )
        return None

    scalars: dict[str, str] = {}
    sources: list[str] = []
    ids: list[str] = []
    for raw_line in match.group("body").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" not in line:
            result.errors.append(f"строка метаданных без ':' — {line!r}")
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key == "source":
            sources.append(value)
        elif key == "id":
            ids.append(value)
        elif key in _REQUIRED_SCALAR_KEYS:
            if key in scalars:
                result.errors.append(f"дублирующийся ключ метаданных: {key}")
            scalars[key] = value
        else:
            result.warnings.append(f"неизвестный ключ метаданных: {key}")

    for key in _REQUIRED_SCALAR_KEYS:
        if key not in scalars:
            result.errors.append(f"в блоке метаданных отсутствует обязательное поле: {key}")

    if scalars.get("status") not in (None, *_VALID_STATUS):
        result.errors.append(
            f"status={scalars.get('status')!r} — допустимо только {sorted(_VALID_STATUS)}"
        )

    if not sources:
        result.errors.append("в блоке метаданных нет ни одной строки 'source: путь@версия'")

    return _ParsedMetadata(scalars=scalars, sources=sources, ids=ids)


def _check_sources(sources: list[str], root: Path, result: LintResult) -> None:
    for entry in sources:
        m = _SOURCE_LINE.match(entry)
        if not m:
            result.errors.append(f"строка source не в формате 'путь@версия': {entry!r}")
            continue
        source_path = root / m.group("path")
        if not source_path.is_file():
            result.errors.append(f"source указывает на несуществующий файл: {m.group('path')}")
            continue
        try:
            doc = load_document(source_path)
        except ValueError as exc:
            result.errors.append(f"не удалось прочитать frontmatter {m.group('path')}: {exc}")
            continue
        actual_version = str(doc.metadata.get("version", "")).strip()
        declared_version = m.group("version")
        if actual_version and actual_version != declared_version:
            result.errors.append(
                f"дрейф версии: схема заявляет {m.group('path')}@{declared_version}, "
                f"фактическая version в frontmatter — {actual_version}. "
                "Схема требует повторной сверки (diagram_geometry_foundations.md §13)."
            )


def _check_ids(declared_ids: list[str], body_text: str, root: Path, result: LintResult) -> None:
    # An empty `id` list is legitimate for a diagram that traces no registry
    # element at all — an ad-hoc process illustration, or a template skeleton
    # (diagram_geometry_foundations.md §13, process_diagram_style_guide.md
    # §2.1: "id не обязателен... строк id может не быть вовсе"). Such a
    # diagram still requires the metadata block and its `source` lines
    # (enforced above); it just carries nothing here to cross-check against
    # the traceability registry. A diagram that DOES declare at least one id
    # is still held to the full checks below: unknown ids, missing
    # data-spec-id coverage, and untracked extra data-spec-id all still
    # apply.
    if not declared_ids:
        body_ids = {_normalize_id(i) for i in _DATA_SPEC_ID.findall(body_text)}
        for identifier in sorted(body_ids):
            result.errors.append(
                f'элемент схемы несёт data-spec-id="{identifier}", '
                "но этот id не заявлен в блоке метаданных"
            )
        return

    known = collect_traceable_elements(root)
    declared_normalized = {_normalize_id(i) for i in declared_ids}
    for identifier in declared_ids:
        normalized = _normalize_id(identifier)
        if normalized not in known:
            result.errors.append(
                f"заявленный id {identifier!r} не найден ни в одной спецификации "
                "(проверено через тот же реестр, что использует traceability для .md-документов)"
            )

    body_ids = {_normalize_id(i) for i in _DATA_SPEC_ID.findall(body_text)}
    missing_in_body = declared_normalized - body_ids
    for identifier in sorted(missing_in_body):
        result.errors.append(
            f"id {identifier} заявлен в метаданных, но ни один элемент схемы "
            f'не несёт data-spec-id="{identifier}"'
        )
    extra_in_body = body_ids - declared_normalized
    for identifier in sorted(extra_in_body):
        result.errors.append(
            f'элемент схемы несёт data-spec-id="{identifier}", '
            "но этот id не заявлен в блоке метаданных"
        )


def _classes(element: ElementTree.Element) -> set[str]:
    return set((element.get("class") or "").split())


def _local_tag(element: ElementTree.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _parent_map(root_el: ElementTree.Element) -> dict[ElementTree.Element, ElementTree.Element]:
    return {child: parent for parent in root_el.iter() for child in parent}


def _bound_spec_ids(
    element: ElementTree.Element,
    parents: dict[ElementTree.Element, ElementTree.Element],
) -> set[str]:
    result: set[str] = set()
    current: ElementTree.Element | None = element
    while current is not None:
        identifier = current.get("data-spec-id")
        if identifier:
            result.add(_normalize_id(identifier))
        current = parents.get(current)
    return result


def _check_legend_id_families(
    root_el: ElementTree.Element, declared_ids: list[str], result: LintResult
) -> None:
    declared_families: set[str] = set()
    for identifier in declared_ids:
        match = _ID_FAMILY.fullmatch(_normalize_id(identifier))
        if match:
            declared_families.add(f"{match.group('family')}_*")
    if not declared_families:
        return

    legend_families: set[str] = set()
    for element in root_el.iter():
        if "legend-id" not in _classes(element):
            continue
        text = "".join(element.itertext()).strip().upper()
        match = _LEGEND_FAMILY.fullmatch(text)
        if match:
            legend_families.add(f"{match.group('family')}_*")

    if not legend_families:
        if len(declared_families) > 1:
            result.errors.append(
                "легенда не перечисляет семейства идентификаторов: "
                + ", ".join(sorted(declared_families))
            )
        return

    missing = sorted(declared_families - legend_families)
    if missing:
        result.errors.append(
            "в легенде отсутствуют используемые семейства идентификаторов: " + ", ".join(missing)
        )
    extra = sorted(legend_families - declared_families)
    if extra:
        result.errors.append(
            "легенда содержит неиспользуемые семейства идентификаторов: " + ", ".join(extra)
        )


def _check_flow_label_bindings(root_el: ElementTree.Element, result: LintResult) -> None:
    parents = _parent_map(root_el)
    for element in root_el.iter():
        classes = _classes(element)
        if not classes.intersection({"flow-text", "control-flow-text"}):
            continue
        label = " ".join("".join(element.itertext()).split())
        if "_XXX" in label:
            continue
        bound = _bound_spec_ids(element, parents)
        visible_ids = {
            _normalize_id(value) for value in _VISIBLE_FLOW_ID.findall("".join(element.itertext()))
        }
        missing = sorted(visible_ids - bound)
        if missing:
            result.errors.append(
                "видимая подпись потока не связана с указанными ID через data-spec-id: "
                + ", ".join(missing)
            )

        inside_component = any(
            identifier.startswith(("ARC_CMP_", "INF_CMP_")) for identifier in bound
        )
        has_flow_binding = any(
            identifier.startswith(("ARC_FLOW_", "INF_FLOW_", "SEC_CTL_")) for identifier in bound
        )
        if not inside_component and not has_flow_binding:
            result.errors.append(
                f"внешняя подпись потока {label!r} не имеет data-spec-id "
                "существующего ARC_FLOW_*, INF_FLOW_* или SEC_CTL_*"
            )


def _check_arc_flow_label_fills(root_el: ElementTree.Element, result: LintResult) -> None:
    """Require every visible ARC_FLOW label to sit on a semantic filled shape."""

    parents = _parent_map(root_el)
    by_id = {element.get("id"): element for element in root_el.iter() if element.get("id")}
    for element in root_el.iter():
        if _local_tag(element) != "text" or "legend-id" in _classes(element):
            continue
        label = " ".join("".join(element.itertext()).split())
        if _VISIBLE_ARC_FLOW_ID.search(label) is None:
            continue
        try:
            x = float(element.get("x"))
            y = float(element.get("y"))
        except (TypeError, ValueError):
            result.errors.append(
                f"видимая подпись ARC_FLOW {label!r} обязана иметь числовые x и y "
                "для проверки заливки"
            )
            continue
        parent = parents.get(element)
        candidates = list(parent) if parent is not None else list(root_el)
        containing: list[tuple[float, ElementTree.Element]] = []
        for candidate in candidates:
            if _local_tag(candidate) != "rect":
                continue
            try:
                rect_x = float(candidate.get("x", "0"))
                rect_y = float(candidate.get("y", "0"))
                width = float(candidate.get("width"))
                height = float(candidate.get("height"))
            except (TypeError, ValueError):
                continue
            if rect_x <= x <= rect_x + width and rect_y <= y <= rect_y + height:
                containing.append((width * height, candidate))
        if not containing:
            result.errors.append(
                f"видимая подпись ARC_FLOW {label!r} не помещена в залитую плашку или карточку"
            )
            continue
        container = min(containing, key=lambda item: item[0])[1]
        if not _classes(container).intersection(_ARC_FLOW_FILL_CLASSES):
            result.errors.append(
                f"видимая подпись ARC_FLOW {label!r} находится в контейнере без "
                "семантической заливки"
            )
            continue
        label_palettes = _palette_for(_classes(container), _FLOW_LABEL_PALETTE_CLASSES)
        if not label_palettes:
            continue
        connector_ref = container.get("data-connector-ref")
        if not connector_ref:
            result.errors.append(
                f"плашка ARC_FLOW {label!r} обязана задать data-connector-ref, "
                "чтобы её цвет проверялся по стрелке"
            )
            continue
        connector = by_id.get(connector_ref)
        if connector is None or _local_tag(connector) != "path":
            result.errors.append(
                f"data-connector-ref={connector_ref!r} у плашки ARC_FLOW {label!r} "
                "не указывает на существующий <path>"
            )
            continue
        connector_palettes = _palette_for(_classes(connector), _CONNECTOR_PALETTE_CLASSES)
        match = _match_palettes(label_palettes, connector_palettes)
        if match in ("a_ambiguous", "b_ambiguous"):
            result.errors.append(
                f"плашка ARC_FLOW {label!r} или её стрелка не имеет ровно одной "
                "поддерживаемой цветовой категории"
            )
        elif match == "mismatch":
            result.errors.append(
                f"цвет плашки ARC_FLOW {label!r} не совпадает с цветом стрелки {connector_ref!r}"
            )


def _check_all_flow_label_connectors(root_el: ElementTree.Element, result: LintResult) -> None:
    """Every flow-label plaque is bound to one existing connector of its palette."""

    by_id = {element.get("id"): element for element in root_el.iter() if element.get("id")}
    for plaque in root_el.iter():
        label_palettes = _palette_for(_classes(plaque), _FLOW_LABEL_PALETTE_CLASSES)
        if not label_palettes:
            continue
        plaque_id = plaque.get("id", "<без id>")
        connector_ref = plaque.get("data-connector-ref")
        if not connector_ref:
            result.errors.append(f"плашка потока {plaque_id!r} обязана задать data-connector-ref")
            continue
        connector = by_id.get(connector_ref)
        if connector is None or _local_tag(connector) != "path":
            result.errors.append(
                f"data-connector-ref={connector_ref!r} у плашки {plaque_id!r} "
                "не указывает на существующий <path>"
            )
            continue
        connector_palettes = _palette_for(_classes(connector), _CONNECTOR_PALETTE_CLASSES)
        match = _match_palettes(label_palettes, connector_palettes)
        if match in ("a_ambiguous", "b_ambiguous"):
            result.errors.append(
                f"плашка {plaque_id!r} или её стрелка не имеет ровно одной цветовой категории"
            )
        elif match == "mismatch":
            result.errors.append(
                f"цвет плашки {plaque_id!r} не совпадает с цветом стрелки: "
                f"плашка={next(iter(label_palettes))}, "
                f"линия={next(iter(connector_palettes))}"
            )


def _palette_for(classes: set[str], mapping: dict[str, set[str]]) -> set[str]:
    return {palette for palette, candidates in mapping.items() if classes & candidates}


_PaletteMatch = Literal["ok", "a_ambiguous", "b_ambiguous", "mismatch"]


def _match_palettes(a_palettes: set[str], b_palettes: set[str]) -> _PaletteMatch:
    """Classify one side of a colour-inheritance check against the other.

    The three call sites below (`_check_arc_flow_label_fills`,
    `_check_all_flow_label_connectors`, `_check_connector_source_colors`)
    each require exactly one supported palette on both sides and then
    compare them -- the same three-way branch, previously written out
    separately in each. Only the comparison is shared; each caller keeps
    its own error wording, since "плашка ARC_FLOW" and "источник" are not
    interchangeable in the message a reader sees.
    """

    if len(a_palettes) != 1:
        return "a_ambiguous"
    if len(b_palettes) != 1:
        return "b_ambiguous"
    return "ok" if a_palettes == b_palettes else "mismatch"


def _check_connector_source_colors(root_el: ElementTree.Element, result: LintResult) -> None:
    by_id = {element.get("id"): element for element in root_el.iter() if element.get("id")}
    for element in root_el.iter():
        classes = _classes(element)
        is_direct = bool(classes.intersection(_DIRECT_CONNECTOR_CLASSES))
        source_ref = element.get("data-source-ref")
        shared_route = element.get("data-shared-route") == "true"
        if is_direct and bool(source_ref) == shared_route:
            result.errors.append(
                "прямой коннектор обязан нести ровно одно из data-source-ref "
                'или data-shared-route="true"'
            )
            continue
        if not is_direct and not source_ref:
            continue
        if source_ref and shared_route:
            result.errors.append(
                'коннектор не может одновременно нести data-source-ref и data-shared-route="true"'
            )
            continue
        if shared_route:
            continue

        source = by_id.get(source_ref)
        if source is None:
            result.errors.append(
                f"data-source-ref={source_ref!r} указывает на отсутствующий элемент"
            )
            continue
        source_palettes = _palette_for(_classes(source), _SOURCE_PALETTE_CLASSES)
        connector_palettes = _palette_for(classes, _CONNECTOR_PALETTE_CLASSES)
        match = _match_palettes(source_palettes, connector_palettes)
        if match == "a_ambiguous":
            result.errors.append(
                f"источник {source_ref!r} не имеет ровно одной поддерживаемой цветовой категории"
            )
            continue
        if match == "b_ambiguous":
            result.errors.append(
                f"коннектор от {source_ref!r} не имеет ровно одного класса цвета линии"
            )
            continue
        if match == "mismatch":
            result.errors.append(
                f"цвет коннектора от {source_ref!r} не совпадает с цветом источника: "
                f"источник={next(iter(source_palettes))}, линия={next(iter(connector_palettes))}"
            )


def _check_visible_id_separators(root_el: ElementTree.Element, result: LintResult) -> None:
    """Forbid slash-separated architectural IDs in visible diagram labels."""

    for element in root_el.iter():
        if _local_tag(element) != "text":
            continue
        label = " ".join("".join(element.itertext()).split())
        if _ID_SLASH_SEPARATOR.search(label) is not None:
            result.errors.append(
                f"видимая подпись {label!r} разделяет архитектурные ID символом '/'; "
                "разные элементы разделяются точкой '·'"
            )


def _is_architecture_diagram(
    root_el: ElementTree.Element,
    declared_ids: list[str],
) -> bool:
    return root_el.get("data-diagram-kind") == "architecture" or any(
        _normalize_id(identifier).startswith(_ARCHITECTURE_ID_PREFIXES)
        for identifier in declared_ids
    )


def _check_architecture_semantics(
    root_el: ElementTree.Element,
    declared_ids: list[str],
    result: LintResult,
) -> None:
    if not _is_architecture_diagram(root_el, declared_ids):
        return
    _check_flow_label_bindings(root_el, result)
    _check_arc_flow_label_fills(root_el, result)
    _check_connector_source_colors(root_el, result)
    _check_visible_id_separators(root_el, result)
    _check_legend_id_families(root_el, declared_ids, result)


def _architecture_reference_gaps(
    root: Path,
    required_kinds: set[str],
    result: LintResult,
) -> dict[str, float] | None:
    template = root / ARCHITECTURE_TEMPLATE_RELATIVE
    if not template.is_file():
        result.errors.append(
            "не найден архитектурный SVG-шаблон: невозможно геометрически вычислить просветы"
        )
        return None
    measured = check_geometry(read_text(template))
    if measured.errors:
        result.errors.append(
            "геометрия архитектурного SVG-шаблона не позволяет вычислить просветы: "
            + "; ".join(measured.errors)
        )
        return None
    references: dict[str, float] = {}
    for kind in required_kinds:
        values = {gap.value for gap in measured.vertical_gaps if gap.kind == kind}
        if len(values) != 1:
            result.errors.append(
                "архитектурный SVG-шаблон должен геометрически задавать ровно одно "
                f"значение {kind}-gap через data-gap-from"
            )
            return None
        references[kind] = values.pop()
    return references


def _architecture_reference_transition_layout(
    root: Path,
    result: LintResult,
) -> ControlTransitionLayout | None:
    template = root / ARCHITECTURE_TEMPLATE_RELATIVE
    if not template.is_file():
        result.errors.append(
            "не найден архитектурный SVG-шаблон: невозможно вычислить геометрию "
            "контрольного перехода"
        )
        return None
    measured = check_geometry(read_text(template))
    if measured.errors:
        result.errors.append(
            "геометрия архитектурного SVG-шаблона не позволяет вычислить контрольный "
            "переход: " + "; ".join(measured.errors)
        )
        return None
    if len(measured.control_transition_layouts) != 1:
        result.errors.append(
            "архитектурный SVG-шаблон должен геометрически задавать ровно один "
            'data-layout="control-transition"'
        )
        return None
    return measured.control_transition_layouts[0]


def _architecture_reference_port_gap(root: Path, result: LintResult) -> float | None:
    template = root / ARCHITECTURE_TEMPLATE_RELATIVE
    if not template.is_file():
        result.errors.append(
            "не найден архитектурный SVG-шаблон: невозможно вычислить right-port-gap"
        )
        return None
    measured = check_geometry(read_text(template))
    if measured.errors:
        result.errors.append(
            "геометрия архитектурного SVG-шаблона не позволяет вычислить "
            "right-port-gap: " + "; ".join(measured.errors)
        )
        return None
    values = {gap.value for gap in measured.port_gaps}
    if len(values) != 1:
        result.errors.append(
            "архитектурный SVG-шаблон должен геометрически задавать ровно один "
            "right-port-gap через data-port-group"
        )
        return None
    return values.pop()


def _architecture_reference_flow_label_layouts(
    root: Path, result: LintResult
) -> dict[str, FlowLabelLayout] | None:
    template = root / ARCHITECTURE_TEMPLATE_RELATIVE
    if not template.is_file():
        result.errors.append(
            "не найден архитектурный SVG-шаблон: невозможно вычислить геометрию плашки потока"
        )
        return None
    measured = check_geometry(read_text(template))
    if measured.errors:
        result.errors.append(
            "геометрия архитектурного SVG-шаблона не позволяет вычислить плашку потока: "
            + "; ".join(measured.errors)
        )
        return None
    layouts = {layout.kind: layout for layout in measured.flow_label_layouts}
    required = {"flow-label", "flow-label-multiline"}
    if set(layouts) != required or len(measured.flow_label_layouts) != len(required):
        result.errors.append(
            "архитектурный SVG-шаблон должен геометрически задавать ровно по одной "
            "одно- и двухстрочной плашке потока"
        )
        return None
    return layouts


def _architecture_reference_flow_caption_padding(root: Path, result: LintResult) -> float | None:
    """Measure the shared `space-m` flow-caption padding from the registered
    architecture template rather than assuming a literal -- both diagram
    families (architecture and process) use the same token, so a single
    template stays the one source of truth for it, matching how gaps,
    transition layouts and port spacing are already measured here."""

    template = root / ARCHITECTURE_TEMPLATE_RELATIVE
    if not template.is_file():
        result.errors.append(
            "не найден архитектурный SVG-шаблон: невозможно вычислить боковой отступ flow-caption"
        )
        return None
    value, errors = measure_reference_flow_caption_padding(read_text(template))
    result.errors.extend(errors)
    return value


def _check_visible_meta(scalars: dict[str, str], body_text: str, result: LintResult) -> None:
    r"""Header содержит видимую строку версии/даты, читаемую человеком без
    обращения к исходнику (diagram_geometry_foundations.md §5, §13.1) —
    `<text data-diagram-meta="version">Версия N · Обновлено ...</text>`.
    Её отсутствие для любой схемы, соблюдающей контракт метаданных, —
    ошибка того же рода, что отсутствие обязательного поля метаданных.

    Если найденный текст содержит числовой токен версии (`\d+\.\d+`), он
    обязан буквально совпадать с `diagram_version`; аналогично для даты и
    времени внутри `generated_at`. Шаблонные скелеты намеренно несут
    нечисловые плейсхолдеры («Версия X.Y · Обновлено ГГГГ-ММ-ДД ЧЧ:ММ») —
    отсутствие числового токена version/date/time тихо пропускает
    соответствующее сравнение, а не считается ошибкой: сверять плейсхолдер
    не с чем, и это отличает шаблон от реальной схемы без служебного флага
    «это шаблон» (diagram_geometry_foundations.md §13.1).

    Область: `diagram_version` здесь двухкомпонентный (`N.N`), как во всех
    текущих схемах репозитория; трёхкомпонентный semver `_VERSION_TOKEN` не
    захватит целиком.
    """

    match = _VISIBLE_META.search(body_text)
    if match is None:
        result.errors.append(
            "в header отсутствует видимая строка версии "
            '(элемент с data-diagram-meta="version"), см. '
            "diagram_geometry_foundations.md §13.1"
        )
        return

    caption = match.group("text")

    version_token = _VERSION_TOKEN.search(caption)
    if version_token is not None:
        declared_version = scalars.get("diagram_version", "")
        if version_token.group(0) != declared_version:
            result.errors.append(
                f"видимая строка версии в header заявляет {version_token.group(0)!r}, "
                f"а diagram_version в метаданных — {declared_version!r}. Значения обязаны "
                "совпадать (diagram_geometry_foundations.md §13.1)."
            )

    generated_at = scalars.get("generated_at", "")

    caption_date = _DATE_TOKEN.search(caption)
    if caption_date is not None:
        metadata_date = _DATE_TOKEN.search(generated_at)
        if metadata_date is None or caption_date.group(0) != metadata_date.group(0):
            result.errors.append(
                f"видимая строка версии в header показывает дату {caption_date.group(0)!r}, "
                f"а generated_at в метаданных — {generated_at!r}. Даты обязаны совпадать "
                "(diagram_geometry_foundations.md §13.1)."
            )

    caption_time = _TIME_TOKEN.search(caption)
    if caption_time is not None:
        metadata_time = _TIME_TOKEN.search(generated_at)
        if metadata_time is None or caption_time.group(0) != metadata_time.group(0):
            result.errors.append(
                f"видимая строка версии в header показывает время {caption_time.group(0)!r}, "
                f"но generated_at в метаданных не содержит совпадающего времени "
                f"({generated_at!r}). Схема с видимым временем обязана нести полный "
                "generated_at с этим же временем (diagram_geometry_foundations.md §13.1)."
            )


def _check_structure(text: str, result: LintResult) -> ElementTree.Element | None:
    try:
        root_el = ElementTree.fromstring(text)
    except (ElementTree.ParseError, DefusedXmlException) as exc:
        result.errors.append(f"файл не является корректным XML/SVG: {exc}")
        return None

    tag = root_el.tag
    if tag not in (f"{_SVG_NS}svg", "svg"):
        result.errors.append(f"корневой элемент не <svg>: {tag}")
        return None

    width = root_el.get("width")
    height = root_el.get("height")
    view_box = root_el.get("viewBox")
    if not view_box:
        result.errors.append("отсутствует viewBox на корневом <svg>")
    elif width and height:
        try:
            _, _, vb_w, vb_h = (float(part) for part in view_box.split())
            if abs(float(width) - vb_w) > 1e-9 or abs(float(height) - vb_h) > 1e-9:
                result.errors.append(
                    f"viewBox ({vb_w}x{vb_h}) не совпадает с width/height ({width}x{height})"
                )
        except ValueError:
            result.errors.append(f"не удалось разобрать числа в viewBox={view_box!r}")

    def _find_local(name: str) -> ElementTree.Element | None:
        for el in root_el.iter():
            if _local_tag(el) == name:
                return el
        return None

    title_el = _find_local("title")
    if title_el is None or not (title_el.text or "").strip():
        result.errors.append('отсутствует непустой <title> — обязателен для role="img"')
    desc_el = _find_local("desc")
    if desc_el is None or not (desc_el.text or "").strip():
        result.errors.append("отсутствует непустой <desc>")
    if root_el.get("role") != "img":
        result.errors.append('корневой <svg> должен иметь role="img"')
    if not root_el.get("aria-labelledby"):
        result.errors.append("отсутствует aria-labelledby на корневом <svg>")
    return root_el


def _check_dead_definitions(text: str, root_el: ElementTree.Element, result: LintResult) -> None:
    """Раздел 15 стандарта: неиспользуемые маркеры, классы и элементы удаляются.

    Мёртвое определение ничего не ломает визуально, поэтому не обнаруживается
    ни рендерингом, ни ручным просмотром, и накапливается от правки к правке.
    Проверка сверяет объявленные CSS-классы и `<marker>` с фактическими
    ссылками на них: `class="..."` в теле схемы и `url(#...)` в стилях и
    атрибутах. Обратное направление (использован необъявленный класс)
    проверяется тем же сопоставлением.
    """

    used_classes: set[str] = set()
    for element in root_el.iter():
        class_attr = element.get("class")
        if class_attr:
            used_classes.update(class_attr.split())

    declared_classes: set[str] = set()
    for style_match in _STYLE_BLOCK.finditer(text):
        declared_classes.update(
            match.group("name") for match in _CLASS_RULE.finditer(style_match.group("body"))
        )

    dead_classes = sorted(declared_classes - used_classes)
    if dead_classes:
        result.errors.append(
            "объявлены, но не используются CSS-классы: "
            + ", ".join(f".{name}" for name in dead_classes)
            + " — удалите их (раздел 15 стандарта)"
        )

    undeclared_classes = sorted(used_classes - declared_classes)
    if undeclared_classes:
        result.errors.append(
            "используются необъявленные CSS-классы: "
            + ", ".join(f".{name}" for name in undeclared_classes)
        )

    declared_markers = {match.group("name") for match in _MARKER_ID.finditer(text)}
    referenced = {match.group("name") for match in _URL_REF.finditer(text)}
    dead_markers = sorted(declared_markers - referenced)
    if dead_markers:
        result.errors.append(
            "объявлены, но не используются маркеры: "
            + ", ".join(f"#{name}" for name in dead_markers)
            + " — удалите их (раздел 15 стандарта)"
        )

    # url(#...) адресует не только маркеры (градиенты, фильтры, clipPath), поэтому
    # незакрытой ссылкой считается только та, для которой в файле нет элемента с
    # таким id вообще.
    defined_ids = {element.get("id") for element in root_el.iter() if element.get("id")}
    missing_targets = sorted(referenced - defined_ids)
    if missing_targets:
        result.errors.append(
            "ссылка на неопределённый элемент: " + ", ".join(f"#{name}" for name in missing_targets)
        )


def _display_name(path: Path, root: Path) -> str:
    try:
        return relative_posix(path, root)
    except ValueError:
        return str(path)


def lint_file(path: Path, root: Path) -> LintResult:
    result = LintResult(file=_display_name(path, root))
    text = read_text(path)

    root_el = _check_structure(text, result)
    if root_el is not None:
        _check_dead_definitions(text, root_el, result)
        _check_all_flow_label_connectors(root_el, result)

    metadata = _parse_metadata_block(text, result)
    if metadata is not None:
        _check_sources(metadata.sources, root, result)
        _check_ids(metadata.ids, text, root, result)
        _check_visible_meta(metadata.scalars, text, result)
        if root_el is not None:
            _check_architecture_semantics(root_el, metadata.ids, result)

    declared_ids = metadata.ids if metadata is not None else []
    has_referenced_gap = root_el is not None and any(
        element.get("data-gap-from") is not None for element in root_el.iter()
    )
    reference_gaps = None
    reference_transition_layout = None
    reference_port_gap = None
    reference_flow_label_layouts = None
    reference_card_text_inset = None
    if root_el is not None and _is_architecture_diagram(root_el, declared_ids):
        template_path = root / ARCHITECTURE_TEMPLATE_RELATIVE
        if template_path.is_file():
            template_text = read_text(template_path)
            if 'id="template-component"' in template_text:
                reference_card_text_inset, inset_errors = measure_reference_card_text_inset(
                    template_text
                )
                result.errors.extend(inset_errors)
    if (
        root_el is not None
        and has_referenced_gap
        and _is_architecture_diagram(root_el, declared_ids)
    ):
        required_gap_kinds = {
            element.get("data-gap-kind", "layer")
            for element in root_el.iter()
            if element.get("data-gap-from") is not None
        }
        reference_gaps = _architecture_reference_gaps(root, required_gap_kinds, result)

    has_control_transition = root_el is not None and any(
        element.get("data-layout") == "control-transition" for element in root_el.iter()
    )
    architecture_template = root / ARCHITECTURE_TEMPLATE_RELATIVE
    if (
        root_el is not None
        and has_control_transition
        and _is_architecture_diagram(root_el, declared_ids)
        and path.resolve() != architecture_template.resolve()
    ):
        reference_transition_layout = _architecture_reference_transition_layout(root, result)

    has_port_groups = root_el is not None and any(
        element.get("data-port-group") is not None for element in root_el.iter()
    )
    if (
        root_el is not None
        and has_port_groups
        and _is_architecture_diagram(root_el, declared_ids)
        and path.resolve() != architecture_template.resolve()
    ):
        reference_port_gap = _architecture_reference_port_gap(root, result)

    has_flow_labels = root_el is not None and any(
        _classes(element).intersection(_FLOW_LABEL_CLASSES) for element in root_el.iter()
    )
    if (
        root_el is not None
        and has_flow_labels
        and _is_architecture_diagram(root_el, declared_ids)
        and path.resolve() != architecture_template.resolve()
    ):
        reference_flow_label_layouts = _architecture_reference_flow_label_layouts(root, result)

    geometry = check_geometry(
        text,
        reference_gaps=reference_gaps,
        reference_transition_layout=reference_transition_layout,
        reference_port_gap=reference_port_gap,
        reference_flow_label_layouts=reference_flow_label_layouts,
        reference_card_text_inset=reference_card_text_inset,
    )
    result.errors.extend(geometry.errors)
    result.warnings.extend(geometry.warnings)

    return result


def default_targets(root: Path) -> list[Path]:
    """Поставленные схемы плюс шаблонные скелеты.

    Шаблоны из operations/architecture/templates/ обязаны проходить те же
    проверки (diagram_geometry_foundations.md §15.1) — они демонстрируют
    эталонную геометрию, и их копируют. Пока они лежали вне цели по
    умолчанию, обязанность существовала только на словах: дефекты шаблона
    не видел ни один автоматический прогон.
    """

    targets: list[Path] = []
    for relative in (Path("work") / "artefacts", Path("operations") / "architecture" / "templates"):
        directory = root / relative
        if directory.is_dir():
            targets.extend(directory.rglob("*.svg"))
    return sorted(targets)


class _LintResultLike(Protocol):
    file: str
    errors: list[str]

    @property
    def ok(self) -> bool: ...


_ResultT = TypeVar("_ResultT", bound=_LintResultLike)


def run_cli(
    *,
    description: str,
    paths_help: str,
    no_targets_message: str,
    lint_one: Callable[[Path, Path], _ResultT],
    warnings_of: Callable[[_ResultT], list[str]] | None = None,
) -> int:
    """Shared CLI shape for this module's `main()` and diagram_render_lint.py's:
    parse `paths`, resolve targets via `default_targets`, lint each one, print
    PASS/FAIL with its errors (and warnings, when `warnings_of` is given), and
    exit non-zero on any failure. `warnings_of` stays optional rather than a
    field every `_LintResultLike` must carry -- diagram_render_lint.py's own
    result type has no warnings concept yet, and giving it an always-empty
    field just to satisfy a shared shape would be speculative, not shared
    behaviour.
    """

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("paths", nargs="*", type=Path, help=paths_help)
    args = parser.parse_args()
    require_supported_python()
    root = find_project_root(Path.cwd())

    targets = [p if p.is_absolute() else Path.cwd() / p for p in args.paths] or default_targets(
        root
    )
    if not targets:
        print(no_targets_message)
        return 0

    all_ok = True
    total_errors = 0
    total_warnings = 0
    for target in targets:
        if not target.is_file():
            print(f"[FAIL] {target}")
            print(f"  ERROR: файл не найден: {target}")
            all_ok = False
            total_errors += 1
            continue
        result = lint_one(target, root)
        print(f"[{'PASS' if result.ok else 'FAIL'}] {result.file}")
        warnings = warnings_of(result) if warnings_of is not None else []
        for warning in warnings:
            print(f"  WARNING: {warning}")
        for error in result.errors:
            print(f"  ERROR: {error}")
        all_ok = all_ok and result.ok
        total_errors += len(result.errors)
        total_warnings += len(warnings)

    summary = f"Итог: файлов={len(targets)}, errors={total_errors}"
    if warnings_of is not None:
        summary += f", warnings={total_warnings}"
    print(summary)
    return 0 if all_ok else 1


def main() -> int:
    return run_cli(
        description="Проверка архитектурных SVG-схем",
        paths_help="Файлы .svg для проверки. По умолчанию — все work/artefacts/**/*.svg (может быть пусто).",
        no_targets_message="Файлы схем не найдены (work/artefacts/**/*.svg) — проверять нечего.",
        lint_one=lint_file,
        warnings_of=lambda result: result.warnings,
    )


if __name__ == "__main__":
    raise SystemExit(main())
