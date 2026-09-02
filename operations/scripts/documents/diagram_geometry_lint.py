"""Coordinate-based geometry checks for SVG diagrams, factored out of
diagram_lint.py so that module stays focused on metadata/traceability.

Scope, precisely — this module enforces exactly two invariants, both real,
both true today of every checked-in diagram, and both computable from raw
XML attributes without rendering the SVG or resolving an arbitrary
`transform` stack:

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

`right-port-gap`, `layer-gap`, `right-rail-gap` and the nested-bottom-gap
family (diagram_geometry_foundations.md §6, §10) are NOT checked here
either: verifying them correctly requires resolving the full accumulated
`transform` stack (translations here are simple and summable, but nothing
in the format guarantees a diagram never rotates or scales a group) and,
for label-plaque sizing, real text metrics. Faking that resolution would
produce false negatives or false positives on exactly the diagrams most in
need of the check. These remain manual items on the checklist in
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
    return GeometryResult(errors=errors, warnings=warnings)
