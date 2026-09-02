"""Проверка SVG-схем (архитектурных и процессных) на соответствие
operations/architecture/diagram_geometry_foundations.md и предметным гайдам
(architecture_diagram_style_guide.md, process_diagram_style_guide.md).

Вызывается из check.py --all автоматически (см.
diagram_geometry_foundations.md §13). Проверяет только то, что можно
проверить без рендеринга SVG: блок метаданных, дрейф заявленной версии
источника от фактической, наличие каждого заявленного ID в спецификации,
взаимное соответствие списка ID и data-spec-id в теле файла, базовую
структуру (viewBox/title/desc), а также — через diagram_geometry_lint —
узкий набор координатных геометрических инвариантов, честно
задокументированный в diagram_geometry_foundations.md §6.1:
дисциплину половинных координат и единый размер наконечника стрелки.

Не проверяет: контраст, реальное визуальное наложение текста, читаемость
после масштабирования, буквальную кратность 4 px для каждой координаты,
`layer-gap`/`right-port-gap`/`right-rail-gap` — это остаётся ручными
пунктами чек-листа (diagram_geometry_foundations.md §17), поскольку требует
либо измеренного рендеринга текста, либо разрешения произвольного стека
`transform` (поворот, масштаб), которое нельзя сделать корректно без риска
ложных срабатываний.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

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
from operations.scripts.documents.diagram_geometry_lint import check_geometry
from operations.scripts.documents.metadata import load_document
from operations.scripts.documents.traceability import _normalize_id, collect_traceable_elements

_SVG_NS = "{http://www.w3.org/2000/svg}"

_METADATA_BLOCK = re.compile(
    r"<!--\s*diagram-metadata\s*(?P<body>.*?)\s*end-diagram-metadata\s*-->",
    re.DOTALL,
)
_DATA_SPEC_ID = re.compile(r'data-spec-id="([^"]+)"')
_SOURCE_LINE = re.compile(r"^(?P<path>[^@\s]+)@(?P<version>\S+)$")
_REQUIRED_SCALAR_KEYS = ("diagram_id", "diagram_version", "generated_at", "status")
_VALID_STATUS = {"current", "superseded"}


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


def _check_structure(text: str, result: LintResult) -> None:
    try:
        root_el = ElementTree.fromstring(text)
    except (ElementTree.ParseError, DefusedXmlException) as exc:
        result.errors.append(f"файл не является корректным XML/SVG: {exc}")
        return

    tag = root_el.tag
    if tag not in (f"{_SVG_NS}svg", "svg"):
        result.errors.append(f"корневой элемент не <svg>: {tag}")
        return

    width = root_el.get("width")
    height = root_el.get("height")
    view_box = root_el.get("viewBox")
    if not view_box:
        result.errors.append("отсутствует viewBox на корневом <svg>")
    elif width and height:
        try:
            _, _, vb_w, vb_h = (float(part) for part in view_box.split())
            if float(width) != vb_w or float(height) != vb_h:
                result.errors.append(
                    f"viewBox ({vb_w}x{vb_h}) не совпадает с width/height ({width}x{height})"
                )
        except ValueError:
            result.errors.append(f"не удалось разобрать числа в viewBox={view_box!r}")

    def _find_local(name: str) -> ElementTree.Element | None:
        for el in root_el.iter():
            local = el.tag.rsplit("}", 1)[-1]
            if local == name:
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


def _display_name(path: Path, root: Path) -> str:
    try:
        return relative_posix(path, root)
    except ValueError:
        return str(path)


def lint_file(path: Path, root: Path) -> LintResult:
    result = LintResult(file=_display_name(path, root))
    text = read_text(path)

    _check_structure(text, result)

    metadata = _parse_metadata_block(text, result)
    if metadata is not None:
        _check_sources(metadata.sources, root, result)
        _check_ids(metadata.ids, text, root, result)

    geometry = check_geometry(text)
    result.errors.extend(geometry.errors)
    result.warnings.extend(geometry.warnings)

    return result


def default_targets(root: Path) -> list[Path]:
    artefacts_dir = root / "work" / "artefacts"
    if not artefacts_dir.is_dir():
        return []
    return sorted(artefacts_dir.rglob("*.svg"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверка архитектурных SVG-схем")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Файлы .svg для проверки. По умолчанию — все work/artefacts/**/*.svg (может быть пусто).",
    )
    args = parser.parse_args()
    require_supported_python()
    root = find_project_root(Path.cwd())

    targets = [p if p.is_absolute() else Path.cwd() / p for p in args.paths] or default_targets(
        root
    )
    if not targets:
        print("Файлы схем не найдены (work/artefacts/**/*.svg) — проверять нечего.")
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
        result = lint_file(target, root)
        print(f"[{'PASS' if result.ok else 'FAIL'}] {result.file}")
        for warning in result.warnings:
            print(f"  WARNING: {warning}")
        for error in result.errors:
            print(f"  ERROR: {error}")
        all_ok = all_ok and result.ok
        total_errors += len(result.errors)
        total_warnings += len(result.warnings)

    print(f"Итог: файлов={len(targets)}, errors={total_errors}, warnings={total_warnings}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
