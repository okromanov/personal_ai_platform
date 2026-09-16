"""Coordinate-based geometry checks for SVG diagrams, factored out of
diagram_lint.py so that module stays focused on metadata/traceability.

Scope, precisely — this module enforces five invariants that are computable
from raw XML attributes without rendering the SVG:

1. **Half-pixel coordinate discipline.** Every numeric `x`/`y`/`width`/
   `height`/`rx`/`ry`/`x1`/`y1`/`x2`/`y2`/`cx`/`cy`/`r` attribute on a shape
   element, every number embedded in a `<path d="...">`, and every `x`/`y`
   on `<text>`/`<tspan>`, has a fractional part of either `0` or exactly
   `.5` (operations/architecture/diagram_geometry_foundations.md §5: "базовая
   сетка — 4 px... половинные координаты допустимы только для оптического
   центрирования линий толщиной 1 px"). This does NOT check literal
   multiples of 4 px — see "What this deliberately does not check" below.
2. **Arrow-marker-size consistency.** If the SVG defines one or more
   `<marker>` elements (arrowheads), their `markerWidth`/`markerHeight`
   attributes are uniform across all of them
   (diagram_geometry_foundations.md §6, token `arrow-marker-size`).
3. **Referenced vertical gaps.** A rectangle may identify its predecessor
   through `data-gap-from="source-id"`. The linter resolves the accumulated
   translation-only ancestor stack, calculates the actual gap, and compares
   it with the layer gap calculated from the registered architecture
   template. A numeric expected value in `data-gap` is forbidden: geometry
   remains the only source of the measurement.
4. **Centred section dividers.** A horizontal `.section-divider` is placed at
   the exact midpoint between the nearest rectangle row above it and the
   nearest rectangle row below it; the spacing is calculated from geometry,
   never copied into metadata.
5. **Declared direct routes.** A path marked `data-route="direct"` contains
   exactly one horizontal or vertical segment. This lets diagrams state the
   local no-bend contract without pretending the linter can infer obstacles.

What this deliberately does not check, and why
------------------------------------------------
The style guide's prose says coordinates and sizes are "chosen as multiples
of the 4 px grid". A literal per-attribute `value % 4 == 0` check was
prototyped against the real shipped diagram
(work/artefacts/architecture/personal_ai_platform_architecture.svg) before
writing this module, and roughly 45% of its numeric shape attributes are
NOT multiples of 4 — including the two fixed-size tokens the guide itself
documents (`arrow-marker-size` = 6 px, `radius-outer` = 7 px), and many
content-derived composite dimensions (a card height that is the sum of a
title baseline offset, a line-height, and a padding token, none of which
individually lands back on 4). Marker `refX`/`refY` anchor values (e.g.
`8.2`) are also legitimately fractional in a way unrelated to the page
grid. Enforcing literal 4 px multiples here would therefore fail the
already-accepted, hand-tuned production diagram across roughly half its
coordinates — exactly the outcome the calling agent's brief warned against
("don't introduce a rule the shipped example SVG would now fail") — while
weakening the check specifically to make that file pass would be exactly
the self-deception operations/change_process.md and AGENTS.md §5.1
forbid. So this module checks the narrower, literally-true half-pixel
invariant instead, and diagram_geometry_foundations.md §6.1 states this
scope explicitly next to the tokens table, rather than letting a reader
infer more automated coverage than exists.

Unreferenced `right-port-gap`, `layer-gap`, `right-rail-gap` and the
nested-bottom-gap family (diagram_geometry_foundations.md §6, §10) are NOT
inferred here: arbitrary transforms and label plaques require real rendered
geometry. Only pairs linked through `data-gap-from` and translation-only
ancestors are checked; other spacing remains a manual checklist item in
diagram_geometry_foundations.md §17.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from defusedxml import ElementTree  # type: ignore[import-untyped]  # no PEP 561 marker

_SVG_NS = "{http://www.w3.org/2000/svg}"

# Attributes checked per element kind, restricted to attributes that carry a
# page-space coordinate or length (marker refX/refY are internal marker-unit
# anchor tuning values, not page geometry, and are excluded deliberately).
_COORD_ATTRS_BY_LOCAL_TAG: dict[str, tuple[str, ...]] = {
    "rect": ("x", "y", "width", "height", "rx", "ry"),
    "circle": ("cx", "cy", "r"),
    "ellipse": ("cx", "cy", "rx", "ry"),
    "line": ("x1", "y1", "x2", "y2"),
    "text": ("x", "y"),
    "tspan": ("x", "y"),
}

_PATH_NUMBER = re.compile(r"-?\d+\.?\d*")
_ALLOWED_FRACTIONS = (0.0, 0.5)
_TRANSLATE = re.compile(
    r"translate\(\s*(?P<x>-?\d+(?:\.\d+)?)"
    r"(?:[ ,]+(?P<y>-?\d+(?:\.\d+)?))?\s*\)"
)
_DIRECT_PATH = re.compile(
    r"^\s*M\s*(?P<x1>-?\d+(?:\.\d+)?)[ ,]+(?P<y1>-?\d+(?:\.\d+)?)\s*"
    r"(?:"
    r"(?P<axis>[HV])\s*(?P<axis_value>-?\d+(?:\.\d+)?)"
    r"|L\s*(?P<x2>-?\d+(?:\.\d+)?)[ ,]+(?P<y2>-?\d+(?:\.\d+)?)"
    r")\s*$",
    re.IGNORECASE,
)


@dataclass
class GeometryResult:
    errors: list[str]
    warnings: list[str]
    vertical_gaps: list["VerticalGap"] = field(default_factory=list)


@dataclass(frozen=True)
class VerticalGap:
    source_id: str
    target_id: str
    value: float


def _local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _fraction_ok(value: float) -> bool:
    fractional = abs(value - int(value))
    return any(abs(fractional - allowed) < 1e-9 for allowed in _ALLOWED_FRACTIONS)


def _check_half_pixel_discipline(root_el, errors: list[str]) -> None:
    for el in root_el.iter():
        local = _local_tag(el.tag)
        for attr in _COORD_ATTRS_BY_LOCAL_TAG.get(local, ()):
            raw = el.get(attr)
            if raw is None:
                continue
            try:
                value = float(raw)
            except ValueError:
                continue
            if not _fraction_ok(value):
                errors.append(
                    f"<{local} {attr}={raw!r}>: дробная координата — допустима только "
                    "целая часть или ровно .5 (diagram_geometry_foundations.md §6.1)"
                )
        if local == "path":
            d = el.get("d")
            if not d:
                continue
            for match in _PATH_NUMBER.finditer(d):
                value = float(match.group())
                if not _fraction_ok(value):
                    errors.append(
                        f"<path d=...>: число {match.group()!r} внутри 'd' имеет дробную "
                        "координату — допустима только целая часть или ровно .5 "
                        "(diagram_geometry_foundations.md §6.1)"
                    )


def _check_arrow_marker_size(root_el, errors: list[str]) -> None:
    sizes: list[tuple[str, str, str]] = []
    for el in root_el.iter():
        if _local_tag(el.tag) != "marker":
            continue
        marker_id = el.get("id", "<без id>")
        width = el.get("markerWidth")
        height = el.get("markerHeight")
        if width is not None:
            sizes.append((marker_id, "markerWidth", width))
        if height is not None:
            sizes.append((marker_id, "markerHeight", height))

    widths = {value for marker_id, attr, value in sizes if attr == "markerWidth"}
    heights = {value for marker_id, attr, value in sizes if attr == "markerHeight"}
    if len(widths) > 1:
        errors.append(
            f"<marker> markerWidth не единообразен между наконечниками: {sorted(widths)} — "
            "все стрелки обязаны иметь один arrow-marker-size (diagram_geometry_foundations.md §6)"
        )
    if len(heights) > 1:
        errors.append(
            f"<marker> markerHeight не единообразен между наконечниками: {sorted(heights)} — "
            "все стрелки обязаны иметь один arrow-marker-size (diagram_geometry_foundations.md §6)"
        )


def _absolute_vertical_box(
    element,
    parents: dict[object, object],
    errors: list[str],
) -> tuple[float, float] | None:
    try:
        y = float(element.get("y"))
        height = float(element.get("height"))
    except (TypeError, ValueError):
        errors.append(
            "элемент с data-gap-from обязан иметь числовые y и height "
            "(diagram_geometry_foundations.md §6)"
        )
        return None

    current = element
    while current is not None:
        transform = current.get("transform")
        if transform:
            remaining = _TRANSLATE.sub("", transform).strip(" ,")
            if remaining:
                errors.append(
                    "data-gap-from нельзя проверить через transform, отличный от translate(...): "
                    f"{transform!r}"
                )
                return None
            for match in _TRANSLATE.finditer(transform):
                y += float(match.group("y") or 0)
        current = parents.get(current)
    return y, y + height


def _measure_referenced_vertical_gaps(root_el, errors: list[str]) -> list[VerticalGap]:
    parents = {child: parent for parent in root_el.iter() for child in parent}
    by_id = {element.get("id"): element for element in root_el.iter() if element.get("id")}
    gaps: list[VerticalGap] = []
    for element in root_el.iter():
        if element.get("data-gap") is not None:
            errors.append(
                "числовой атрибут data-gap запрещён: ожидаемый интервал не дублируется "
                "в SVG, а вычисляется по геометрии шаблона"
            )
        source_id = element.get("data-gap-from")
        if not source_id:
            continue
        source = by_id.get(source_id)
        if source is None:
            errors.append(f"data-gap-from={source_id!r} указывает на отсутствующий элемент")
            continue
        source_box = _absolute_vertical_box(source, parents, errors)
        target_box = _absolute_vertical_box(element, parents, errors)
        if source_box is None or target_box is None:
            continue
        actual = target_box[0] - source_box[1]
        gaps.append(
            VerticalGap(
                source_id=source_id,
                target_id=element.get("id", "<без id>"),
                value=actual,
            )
        )
    return gaps


def _check_reference_layer_gap(
    gaps: list[VerticalGap], reference_layer_gap: float | None, errors: list[str]
) -> None:
    if reference_layer_gap is None:
        return
    for gap in gaps:
        if abs(gap.value - reference_layer_gap) > 1e-9:
            errors.append(
                f"геометрический просвет {gap.source_id!r} → {gap.target_id!r}: "
                f"эталон шаблона {reference_layer_gap:g} px, фактически {gap.value:g} px "
                "(diagram_geometry_foundations.md §6)"
            )


def _check_centered_section_dividers(root_el, errors: list[str]) -> None:
    parents = {child: parent for parent in root_el.iter() for child in parent}
    for divider in root_el.iter():
        classes = set((divider.get("class") or "").split())
        if "section-divider" not in classes:
            continue
        if _local_tag(divider.tag) != "line":
            errors.append("section-divider обязан быть элементом <line>")
            continue
        try:
            y1 = float(divider.get("y1"))
            y2 = float(divider.get("y2"))
        except (TypeError, ValueError):
            errors.append("section-divider обязан иметь числовые y1 и y2")
            continue
        if abs(y1 - y2) > 1e-9:
            errors.append("section-divider обязан быть горизонтальным")
            continue

        parent = parents.get(divider)
        if parent is None:
            errors.append("section-divider обязан находиться между рядами прямоугольников")
            continue
        siblings = list(parent)
        divider_index = siblings.index(divider)
        upper_bottoms: list[float] = []
        lower_tops: list[float] = []
        for index, sibling in enumerate(siblings):
            if _local_tag(sibling.tag) != "rect":
                continue
            try:
                top = float(sibling.get("y"))
                bottom = top + float(sibling.get("height"))
            except (TypeError, ValueError):
                continue
            if index < divider_index and bottom <= y1:
                upper_bottoms.append(bottom)
            elif index > divider_index and top >= y1:
                lower_tops.append(top)
        if not upper_bottoms or not lower_tops:
            errors.append(
                "section-divider обязан находиться между рядами прямоугольников "
                "сверху и снизу внутри одного родителя"
            )
            continue

        upper_bottom = max(upper_bottoms)
        lower_top = min(lower_tops)
        space_above = y1 - upper_bottom
        space_below = lower_top - y1
        if abs(space_above - space_below) > 1e-9:
            errors.append(
                "section-divider не центрирован между соседними рядами: "
                f"сверху {space_above:g} px, снизу {space_below:g} px "
                "(diagram_geometry_foundations.md §9)"
            )


def _check_direct_routes(root_el, errors: list[str]) -> None:
    for element in root_el.iter():
        route = element.get("data-route")
        if route is None:
            continue
        if route != "direct":
            errors.append(f"неподдерживаемое значение data-route={route!r}")
            continue
        if _local_tag(element.tag) != "path":
            errors.append('data-route="direct" разрешён только для <path>')
            continue
        match = _DIRECT_PATH.fullmatch(element.get("d") or "")
        if match is None:
            errors.append(
                'путь с data-route="direct" обязан состоять ровно из одного '
                "горизонтального или вертикального сегмента"
            )
            continue
        if match.group("axis") is not None:
            continue
        x1 = float(match.group("x1"))
        y1 = float(match.group("y1"))
        x2 = float(match.group("x2"))
        y2 = float(match.group("y2"))
        if abs(x1 - x2) > 1e-9 and abs(y1 - y2) > 1e-9:
            errors.append('путь с data-route="direct" обязан быть горизонтальным или вертикальным')


def check_geometry(text: str, *, reference_layer_gap: float | None = None) -> GeometryResult:
    """Run the coordinate geometry checks against raw SVG text.

    Assumes the caller has already validated the document is well-formed
    XML (diagram_lint.py's structural check runs first and short-circuits
    on parse failure); this function re-parses defensively but does not
    attempt to recover from malformed input beyond reporting it.
    """
    errors: list[str] = []
    warnings: list[str] = []
    try:
        root_el = ElementTree.fromstring(text)
    except Exception:  # noqa: BLE001 - already reported by the structural check
        return GeometryResult(errors=errors, warnings=warnings)

    _check_half_pixel_discipline(root_el, errors)
    _check_arrow_marker_size(root_el, errors)
    vertical_gaps = _measure_referenced_vertical_gaps(root_el, errors)
    _check_reference_layer_gap(vertical_gaps, reference_layer_gap, errors)
    _check_centered_section_dividers(root_el, errors)
    _check_direct_routes(root_el, errors)
    return GeometryResult(errors=errors, warnings=warnings, vertical_gaps=vertical_gaps)
