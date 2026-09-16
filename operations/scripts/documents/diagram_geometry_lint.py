"""Coordinate-based geometry checks for SVG diagrams, factored out of
diagram_lint.py so that module stays focused on metadata/traceability.

Scope, precisely — this module enforces three invariants that are computable
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
3. **Declared vertical gaps.** A rectangle may declare
   `data-gap-from="source-id" data-gap="68"`; the linter resolves the
   accumulated translation-only ancestor stack and verifies the exact gap.
   This makes the standard 68 px separation between major cards executable
   without pretending to solve arbitrary SVG geometry.

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

Undeclared `right-port-gap`, `layer-gap`, `right-rail-gap` and the
nested-bottom-gap family (diagram_geometry_foundations.md §6, §10) are NOT
inferred here: arbitrary transforms and label plaques require real rendered
geometry. Only explicitly annotated vertical gaps with translation-only
ancestors are checked; other spacing remains a manual checklist item in
diagram_geometry_foundations.md §17.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

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


@dataclass
class GeometryResult:
    errors: list[str]
    warnings: list[str]


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


def _check_declared_vertical_gaps(root_el, errors: list[str]) -> None:
    parents = {child: parent for parent in root_el.iter() for child in parent}
    by_id = {element.get("id"): element for element in root_el.iter() if element.get("id")}
    for element in root_el.iter():
        source_id = element.get("data-gap-from")
        if not source_id:
            continue
        source = by_id.get(source_id)
        if source is None:
            errors.append(f"data-gap-from={source_id!r} указывает на отсутствующий элемент")
            continue
        try:
            expected = float(element.get("data-gap", ""))
        except ValueError:
            errors.append(f"элемент с data-gap-from={source_id!r} обязан иметь числовой data-gap")
            continue
        source_box = _absolute_vertical_box(source, parents, errors)
        target_box = _absolute_vertical_box(element, parents, errors)
        if source_box is None or target_box is None:
            continue
        actual = target_box[0] - source_box[1]
        if abs(actual - expected) > 1e-9:
            errors.append(
                f"вертикальный просвет от {source_id!r}: объявлено {expected:g} px, "
                f"фактически {actual:g} px (diagram_geometry_foundations.md §6)"
            )


def check_geometry(text: str) -> GeometryResult:
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
    _check_declared_vertical_gaps(root_el, errors)
    return GeometryResult(errors=errors, warnings=warnings)
