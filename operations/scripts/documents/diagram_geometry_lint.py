"""Coordinate-based geometry checks for SVG diagrams, factored out of
diagram_lint.py so that module stays focused on metadata/traceability.

Scope, precisely — this module enforces ten invariants that are computable
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
   through `data-gap-from="source-id"` and, when needed, classify the relation
   symbolically through `data-gap-kind="transition"` (the default kind is
   `layer`). The linter resolves the accumulated translation-only ancestor
   stack, calculates the actual gap, and compares it with the corresponding
   reference geometry calculated from the registered architecture template.
   A numeric expected value in `data-gap` is forbidden: geometry remains the
   only source of the measurement.
4. **Declared bottom-edge alignment.** A rectangle may name another rectangle
   through `data-align-bottom-with`; their absolute bottom edges must match
   after translation-only transforms are resolved.
5. **Centred section dividers.** A horizontal `.section-divider` is placed at
   the exact midpoint between the nearest rectangle row above it and the
   nearest rectangle row below it; the spacing is calculated from geometry,
   never copied into metadata.
6. **Declared direct routes.** A path marked `data-route="direct"` contains
   exactly one horizontal or vertical segment. This lets diagrams state the
   local no-bend contract without pretending the linter can infer obstacles.
7. **Shared routes stay outside cards.** A path marked
   `data-shared-route="true"` is one direct horizontal or vertical segment
   and may touch a card boundary, but may not enter or cross the interior of
   an independently coloured card. At the boundary the route must be split;
   the outgoing segment then uses `data-source-ref`, so source-colour
   validation applies.
8. **Card text alignment.** The leading text rows of coloured component
   cards align to the same left inset, measured from the registered template
   component. This includes capability cards and standalone transitions,
   but excludes nested cards and flow labels.
9. **Transition-card geometry.** Rectangles marked
   `data-layout="control-transition"` align their centre with the rectangle
   named by `data-center-with`, share height, radius and text-slot geometry,
   and match those properties in the registered architecture template. Width
   is content-derived and checked from rendered ink instead of copied from the
   template.
10. **Connector source attachment.** Every path with `data-source-ref` begins
   on the referenced rectangle's boundary after translation-only transforms
   are resolved. This prevents a visually plausible arrow from hanging in the
   gap below or beside its declared source.
11. **Grouped side-port spacing.** Paths marked with the same `data-port-group`
   end on the declared side of one `data-port-target`; the distance between
   their endpoints matches the port-gap geometry registered in the template.
12. **Flow-label geometry.** Every rectangle whose class is `flow-label-*`
   must declare a supported one- or two-line layout and bind every text row
   through `data-label-for`. Height, radius, centred baselines and text anchors
   are compared with template geometry. Every plaque selects a programmed
   `data-padding-profile`; every row stays on the exact geometric centre, while
   the rendered-padding gate checks the visible ink box without per-label hacks.
   Equal-width groups are checked from geometry rather than copied constants.
   Flow captions and control transitions preserve the font's natural advance:
   `textLength`, `lengthAdjust`, and width-anchor stretching are rejected.
   The shared `space-m` token is declared once on the registered architecture
   template and the rendered-padding gate applies it to real ink boxes.
13. **Declared centre-line alignment.** A rectangle may name another
   rectangle through `data-align-center-with`; their absolute vertical
   centres (the midpoint between the top and bottom edge) must match after
   translation-only transforms are resolved. This lets a side flow-label
   plaque align to a control-transition card's vertical middle instead of
   the shared-row bottom line used by `data-align-bottom-with`.

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
inferred here: arbitrary transforms require real rendered geometry. Layer
pairs must be linked through `data-gap-from`; side ports must be linked through
`data-port-group`. Unlike the earlier opt-in contract, every `flow-label-*`
rectangle is discovered from its class and must declare either
`data-layout="flow-label"` or `data-layout="flow-label-multiline"`; omitting the
attribute cannot bypass the check. Other spacing remains a manual checklist
item in diagram_geometry_foundations.md §17.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from defusedxml import ElementTree  # type: ignore[import-untyped]  # no PEP 561 marker
from defusedxml.common import DefusedXmlException  # type: ignore[import-untyped]  # same package

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
_PATH_START = re.compile(
    r"^\s*M\s*(?P<x>-?\d+(?:\.\d+)?)[ ,]+(?P<y>-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_PATH_SEGMENT = re.compile(r"(?P<command>[MLHV])(?P<args>[^MLHV]*)", re.IGNORECASE)
_INDEPENDENT_CARD_CLASSES = {
    "control-card",
    "data-card",
    "execution-card",
    "neutral-card",
}
_COLOURED_COMPONENT_CLASSES = {"control-card", "data-card", "execution-card"}
_LEADING_TEXT_CLASSES = {"component-id", "component-title", "component-text", "small-text"}
_FLOW_LABEL_CLASSES = {
    "flow-label",
    "flow-label-blue",
    "flow-label-gray",
    "flow-label-green",
    "flow-label-red",
}
_FLOW_LABEL_ROW_COUNTS = {"flow-label": 1, "flow-label-multiline": 2}
_FLOW_LABEL_PADDING_PROFILES = {"flow-caption", "flow-port"}


@dataclass
class GeometryResult:
    errors: list[str]
    warnings: list[str]
    vertical_gaps: list["VerticalGap"] = field(default_factory=list)
    control_transition_layouts: list["ControlTransitionLayout"] = field(default_factory=list)
    port_gaps: list["PortGap"] = field(default_factory=list)
    flow_label_layouts: list["FlowLabelLayout"] = field(default_factory=list)


@dataclass(frozen=True)
class VerticalGap:
    source_id: str
    target_id: str
    kind: str
    value: float


@dataclass(frozen=True)
class LayoutSlot:
    name: str
    class_name: str
    x_offset: float
    y_offset: float
    text_anchor: str


@dataclass(frozen=True)
class ControlTransitionLayout:
    card_id: str
    width: float
    height: float
    radius: float
    slots: tuple[LayoutSlot, ...]
    variant: str = "standard"

    def signature(self) -> tuple[float, float, float, tuple[LayoutSlot, ...]]:
        """Geometry shared by the template and every transition card."""

        return self.width, self.height, self.radius, self.slots

    def rhythm_signature(self) -> tuple[float, float, tuple[LayoutSlot, ...]]:
        """Template-derived geometry excluding the content-derived width."""

        return self.height, self.radius, self.slots


@dataclass(frozen=True)
class PortGap:
    group: str
    target_id: str
    side: str
    value: float


@dataclass(frozen=True)
class FlowLabelLayout:
    label_id: str
    kind: str
    width: float
    height: float
    radius: float
    text_y_offsets: tuple[float, ...]
    text_anchors: tuple[str, ...]

    def signature(self) -> tuple[str, float, float, tuple[float, ...], tuple[str, ...]]:
        """Geometry shared by every flow-label plaque of one layout kind.

        Width remains content-derived for captions and parent-grid-derived for
        ports; rendered padding profiles validate it separately.
        """

        return self.kind, self.height, self.radius, self.text_y_offsets, self.text_anchors


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
        kind = element.get("data-gap-kind", "layer")
        if element.get("data-gap-kind") is not None and not source_id:
            errors.append("data-gap-kind разрешён только вместе с data-gap-from")
            continue
        if not source_id:
            continue
        if kind not in {"layer", "transition"}:
            errors.append(
                f"неподдерживаемое значение data-gap-kind={kind!r}: "
                "допустимы 'layer' и 'transition'"
            )
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
                kind=kind,
                value=actual,
            )
        )
    return gaps


def _check_reference_gaps(
    gaps: list[VerticalGap], reference_gaps: dict[str, float] | None, errors: list[str]
) -> None:
    if reference_gaps is None:
        return
    for gap in gaps:
        reference_gap = reference_gaps.get(gap.kind)
        if reference_gap is None:
            continue
        if abs(gap.value - reference_gap) > 1e-9:
            reference_name = (
                "эталон шаблона" if gap.kind == "layer" else f"эталон шаблона {gap.kind}-gap"
            )
            errors.append(
                f"геометрический просвет {gap.source_id!r} → {gap.target_id!r}: "
                f"{reference_name} {reference_gap:g} px, фактически {gap.value:g} px "
                "(diagram_geometry_foundations.md §6)"
            )


def _check_declared_bottom_alignments(root_el, errors: list[str]) -> None:
    parents = {child: parent for parent in root_el.iter() for child in parent}
    by_id = {element.get("id"): element for element in root_el.iter() if element.get("id")}
    for element in root_el.iter():
        target_id = element.get("data-align-bottom-with")
        if target_id is None:
            continue
        element_id = element.get("id", "<без id>")
        if _local_tag(element.tag) != "rect":
            errors.append("data-align-bottom-with разрешён только для <rect>")
            continue
        target = by_id.get(target_id)
        if target is None:
            errors.append(
                f"data-align-bottom-with={target_id!r} у {element_id!r} "
                "указывает на отсутствующий элемент"
            )
            continue
        if _local_tag(target.tag) != "rect":
            errors.append(
                f"data-align-bottom-with={target_id!r} у {element_id!r} обязан указывать на <rect>"
            )
            continue
        box = _absolute_rect_box(element, parents, errors, contract="выравнивание нижних границ")
        target_box = _absolute_rect_box(
            target, parents, errors, contract="выравнивание нижних границ"
        )
        if box is None or target_box is None:
            continue
        if abs(box[3] - target_box[3]) > 1e-9:
            errors.append(
                f"нижняя граница {element_id!r} не выровнена с {target_id!r}: "
                f"{box[3]:g} px вместо {target_box[3]:g} px"
            )


def _check_declared_center_alignments(root_el, errors: list[str]) -> None:
    parents = {child: parent for parent in root_el.iter() for child in parent}
    by_id = {element.get("id"): element for element in root_el.iter() if element.get("id")}
    for element in root_el.iter():
        target_id = element.get("data-align-center-with")
        if target_id is None:
            continue
        element_id = element.get("id", "<без id>")
        if element.get("data-align-bottom-with") is not None:
            errors.append(
                f"{element_id!r} не может одновременно задавать "
                "data-align-bottom-with и data-align-center-with"
            )
            continue
        if _local_tag(element.tag) != "rect":
            errors.append("data-align-center-with разрешён только для <rect>")
            continue
        target = by_id.get(target_id)
        if target is None:
            errors.append(
                f"data-align-center-with={target_id!r} у {element_id!r} "
                "указывает на отсутствующий элемент"
            )
            continue
        if _local_tag(target.tag) != "rect":
            errors.append(
                f"data-align-center-with={target_id!r} у {element_id!r} обязан указывать на <rect>"
            )
            continue
        box = _absolute_rect_box(
            element, parents, errors, contract="выравнивание вертикальных центров"
        )
        target_box = _absolute_rect_box(
            target, parents, errors, contract="выравнивание вертикальных центров"
        )
        if box is None or target_box is None:
            continue
        center = (box[1] + box[3]) / 2
        target_center = (target_box[1] + target_box[3]) / 2
        if abs(center - target_center) > 1e-9:
            errors.append(
                f"вертикальный центр {element_id!r} не совпадает с {target_id!r}: "
                f"{center:g} px вместо {target_center:g} px"
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


def _direct_path_segment(element) -> tuple[float, float, float, float] | None:
    match = _DIRECT_PATH.fullmatch(element.get("d") or "")
    if match is None:
        return None
    x1 = float(match.group("x1"))
    y1 = float(match.group("y1"))
    axis = match.group("axis")
    if axis is not None:
        axis_value = float(match.group("axis_value"))
        if axis.upper() == "H":
            return x1, y1, axis_value, y1
        return x1, y1, x1, axis_value
    x2 = float(match.group("x2"))
    y2 = float(match.group("y2"))
    if abs(x1 - x2) > 1e-9 and abs(y1 - y2) > 1e-9:
        return None
    return x1, y1, x2, y2


def _absolute_translation(
    element,
    parents: dict[object, object],
    errors: list[str],
    *,
    contract: str,
) -> tuple[float, float] | None:
    x_offset = 0.0
    y_offset = 0.0
    current = element
    while current is not None:
        transform = current.get("transform")
        if transform:
            remaining = _TRANSLATE.sub("", transform).strip(" ,")
            if remaining:
                errors.append(
                    f"{contract} нельзя проверить через transform, отличный от "
                    f"translate(...): {transform!r}"
                )
                return None
            for match in _TRANSLATE.finditer(transform):
                x_offset += float(match.group("x"))
                y_offset += float(match.group("y") or 0)
        current = parents.get(current)
    return x_offset, y_offset


def _absolute_rect_box(
    element,
    parents: dict[object, object],
    errors: list[str],
    *,
    contract: str,
) -> tuple[float, float, float, float] | None:
    try:
        x = float(element.get("x"))
        y = float(element.get("y"))
        width = float(element.get("width"))
        height = float(element.get("height"))
    except (TypeError, ValueError):
        errors.append(f"{contract} требует числовые x, y, width и height")
        return None
    offset = _absolute_translation(element, parents, errors, contract=contract)
    if offset is None:
        return None
    x += offset[0]
    y += offset[1]
    return x, y, x + width, y + height


def _segment_crosses_rect_interior(
    segment: tuple[float, float, float, float],
    box: tuple[float, float, float, float],
) -> bool:
    x1, y1, x2, y2 = segment
    left, top, right, bottom = box
    if abs(x1 - x2) < 1e-9:
        return left < x1 < right and max(min(y1, y2), top) < min(max(y1, y2), bottom)
    return top < y1 < bottom and max(min(x1, x2), left) < min(max(x1, x2), right)


def _check_shared_routes_stay_outside_cards(root_el, errors: list[str]) -> None:
    parents = {child: parent for parent in root_el.iter() for child in parent}
    cards: list[tuple[ElementTree.Element, tuple[float, float, float, float]]] = []
    for element in root_el.iter():
        if _local_tag(element.tag) != "rect":
            continue
        classes = set((element.get("class") or "").split())
        if not classes.intersection(_INDEPENDENT_CARD_CLASSES):
            continue
        box = _absolute_rect_box(
            element,
            parents,
            errors,
            contract="проверку общей трассы относительно карточки",
        )
        if box is not None:
            cards.append((element, box))

    for element in root_el.iter():
        if element.get("data-shared-route") != "true":
            continue
        if _local_tag(element.tag) != "path":
            errors.append('data-shared-route="true" разрешён только для <path>')
            continue
        segment = _direct_path_segment(element)
        if segment is None:
            errors.append(
                'путь с data-shared-route="true" обязан состоять ровно из одного '
                "прямого горизонтального или вертикального сегмента от шины или рельса"
            )
            continue
        offset = _absolute_translation(
            element,
            parents,
            errors,
            contract="проверку общей трассы",
        )
        if offset is None:
            continue
        x1, y1, x2, y2 = segment
        absolute_segment = (
            x1 + offset[0],
            y1 + offset[1],
            x2 + offset[0],
            y2 + offset[1],
        )
        for card, box in cards:
            if not _segment_crosses_rect_interior(absolute_segment, box):
                continue
            card_id = card.get("id", "<без id>")
            errors.append(
                f"shared route проходит через внутреннюю область карточки {card_id!r}: "
                "разделите маршрут на границе и задайте исходящему коннектору "
                "data-source-ref"
            )


def _check_control_transition_layouts(
    root_el,
    errors: list[str],
    reference_layout: ControlTransitionLayout | None,
) -> list[ControlTransitionLayout]:
    parents = {child: parent for parent in root_el.iter() for child in parent}
    by_id = {element.get("id"): element for element in root_el.iter() if element.get("id")}
    layouts: list[ControlTransitionLayout] = []
    for card in root_el.iter():
        if card.get("data-layout") != "control-transition":
            continue
        card_id = card.get("id", "<без id>")
        variant = card.get("data-layout-variant", "standard")
        if variant not in {"standard", "single-detail"}:
            errors.append(
                f"переходная карточка {card_id!r}: неизвестный data-layout-variant={variant!r}"
            )
            continue
        if _local_tag(card.tag) != "rect":
            errors.append('data-layout="control-transition" разрешён только для <rect>')
            continue
        if "control-card" not in set((card.get("class") or "").split()):
            errors.append(
                f"переходная карточка {card_id!r} обязана использовать класс control-card"
            )
            continue
        box = _absolute_rect_box(
            card,
            parents,
            errors,
            contract="сравнение геометрии переходных карточек",
        )
        if box is None:
            continue
        center_with = card.get("data-center-with")
        if not center_with:
            errors.append(f"переходная карточка {card_id!r} обязана задать data-center-with")
        else:
            anchor = by_id.get(center_with)
            if anchor is None:
                errors.append(
                    f"data-center-with={center_with!r} у карточки {card_id!r} "
                    "указывает на отсутствующий элемент"
                )
            elif _local_tag(anchor.tag) != "rect":
                errors.append(
                    f"data-center-with={center_with!r} у карточки {card_id!r} "
                    "обязан указывать на <rect>"
                )
            else:
                anchor_box = _absolute_rect_box(
                    anchor,
                    parents,
                    errors,
                    contract="проверку центрирования переходной карточки",
                )
                if anchor_box is not None:
                    card_center = (box[0] + box[2]) / 2
                    anchor_center = (anchor_box[0] + anchor_box[2]) / 2
                    if abs(card_center - anchor_center) > 1e-9:
                        errors.append(
                            f"переходная карточка {card_id!r} не центрирована с "
                            f"{center_with!r}: ось {card_center:g} px вместо "
                            f"{anchor_center:g} px"
                        )
        try:
            radius = float(card.get("rx"))
        except (TypeError, ValueError):
            errors.append(f"переходная карточка {card_id!r} обязана иметь числовой rx")
            continue
        parent = parents.get(card)
        slots: list[LayoutSlot] = []
        seen_slots: set[str] = set()
        for text_element in list(parent) if parent is not None else []:
            slot = text_element.get("data-layout-slot")
            if slot is None:
                continue
            if _local_tag(text_element.tag) != "text":
                errors.append("data-layout-slot разрешён только для <text>")
                continue
            if slot in seen_slots:
                errors.append(f"переходная карточка {card_id!r} повторяет слот {slot!r}")
                continue
            seen_slots.add(slot)
            try:
                text_x = float(text_element.get("x"))
                text_y = float(text_element.get("y"))
            except (TypeError, ValueError):
                errors.append(f"слот {slot!r} карточки {card_id!r} обязан иметь числовые x и y")
                continue
            offset = _absolute_translation(
                text_element,
                parents,
                errors,
                contract="сравнение внутренних интервалов переходных карточек",
            )
            if offset is None:
                continue
            absolute_x = text_x + offset[0]
            absolute_y = text_y + offset[1]
            text_anchor = text_element.get("text-anchor", "start")
            if text_element.get("data-width-anchor") is not None:
                errors.append(
                    f"слот {slot!r} карточки {card_id!r} не должен задавать "
                    "data-width-anchor: ширина вычисляется по естественной ink-рамке"
                )
            if (
                text_element.get("textLength") is not None
                or text_element.get("lengthAdjust") is not None
            ):
                errors.append(
                    f"слот {slot!r} карточки {card_id!r} не должен задавать "
                    "textLength/lengthAdjust: межбуквенный интервал должен оставаться естественным"
                )
            slots.append(
                LayoutSlot(
                    name=slot,
                    class_name=text_element.get("class", ""),
                    x_offset=absolute_x - box[0],
                    y_offset=absolute_y - box[1],
                    text_anchor=text_anchor,
                )
            )
        if not slots:
            errors.append(f"переходная карточка {card_id!r} не содержит ни одного data-layout-slot")
            continue
        if variant == "single-detail" and seen_slots != {"identity", "title", "detail-1"}:
            errors.append(
                f"переходная карточка {card_id!r} с single-detail обязана содержать "
                "ровно слоты identity, title и detail-1"
            )
            continue
        layout = ControlTransitionLayout(
            card_id=card_id,
            width=box[2] - box[0],
            height=box[3] - box[1],
            radius=radius,
            slots=tuple(sorted(slots, key=lambda item: item.name)),
            variant=variant,
        )
        layouts.append(layout)

    if not layouts:
        return layouts
    peers_by_variant: dict[str, ControlTransitionLayout] = {}
    for layout in layouts:
        peer_reference = peers_by_variant.setdefault(layout.variant, layout)
        if layout.rhythm_signature() != peer_reference.rhythm_signature():
            errors.append(
                f"геометрия переходной карточки {layout.card_id!r} отличается от "
                f"{peer_reference.card_id!r}: высота, выравнивание и внутренние интервалы "
                "однотипных контрольных переходов должны совпадать"
            )
    if reference_layout is not None:
        for layout in layouts:
            reference_slots = reference_layout.slots
            if layout.variant == "single-detail":
                # Preserve the template's bottom inset below the last visible row;
                # all other slot coordinates remain template-derived.
                required = {"identity", "title", "detail-1", "detail-2"}
                by_name = {slot.name: slot for slot in reference_slots}
                if not required <= by_name.keys():
                    errors.append("эталон переходной карточки не содержит обязательные слоты")
                    continue
                bottom_inset = reference_layout.height - by_name["detail-2"].y_offset
                if bottom_inset <= 0:
                    errors.append("эталон переходной карточки задаёт неверный нижний отступ")
                    continue
                expected_height = by_name["detail-1"].y_offset + bottom_inset
                reference_slots = tuple(slot for slot in reference_slots if slot.name != "detail-2")
            else:
                expected_height = reference_layout.height
            reference_signature = (
                expected_height,
                reference_layout.radius,
                reference_slots,
            )
            if layout.rhythm_signature() != reference_signature:
                errors.append(
                    f"геометрия переходной карточки {layout.card_id!r} отличается от "
                    "эталона architecture_diagram_template.svg: высота, радиус и "
                    "внутренние интервалы вычисляются по шаблону"
                )
    return layouts


def measure_reference_card_text_inset(template_text: str) -> tuple[float | None, list[str]]:
    """Read the outer component's leading text inset from the SVG template."""
    errors: list[str] = []
    try:
        root = ElementTree.fromstring(template_text)
    except Exception:  # noqa: BLE001 - report a malformed template to the caller
        return None, ["не удалось разобрать SVG-шаблон для отступа текста карточки"]
    component = next((el for el in root.iter() if el.get("id") == "template-component"), None)
    if component is None:
        return None, ["SVG-шаблон не содержит template-component"]
    parents = {child: parent for parent in root.iter() for child in parent}
    parent = parents.get(component)
    if parent is None:
        return None, ["template-component не имеет контейнера"]
    first_text = next(
        (
            el
            for el in list(parent)[list(parent).index(component) + 1 :]
            if _local_tag(el.tag) == "text" and "component-id" in (el.get("class") or "").split()
        ),
        None,
    )
    if first_text is None:
        return None, ["SVG-шаблон не содержит строки component-id в template-component"]
    try:
        inset = float(first_text.get("x")) - float(component.get("x"))
    except (TypeError, ValueError):
        return None, ["SVG-шаблон задаёт нечисловой левый отступ карточки"]
    if inset <= 0:
        errors.append("SVG-шаблон задаёт неверный левый отступ карточки")
        return None, errors
    return inset, errors


def _check_coloured_card_text_alignment(root_el, inset: float, errors: list[str]) -> None:
    parents = {child: parent for parent in root_el.iter() for child in parent}
    for parent in root_el.iter():
        children = list(parent)
        for index, card in enumerate(children):
            if _local_tag(card.tag) != "rect" or not (
                set((card.get("class") or "").split()) & _COLOURED_COMPONENT_CLASSES
            ):
                continue
            box = _absolute_rect_box(card, parents, errors, contract="выравнивание текста карточки")
            if box is None:
                continue
            card_id = card.get("id", "<без id>")
            for text_element in children[index + 1 :]:
                if _local_tag(text_element.tag) == "rect":
                    break  # Nested objects and their centred labels have their own layout.
                if _local_tag(text_element.tag) != "text" or not (
                    set((text_element.get("class") or "").split()) & _LEADING_TEXT_CLASSES
                ):
                    continue
                offset = _absolute_translation(
                    text_element, parents, errors, contract="выравнивание текста карточки"
                )
                if offset is None:
                    continue
                try:
                    x = float(text_element.get("x")) + offset[0]
                except (TypeError, ValueError):
                    errors.append(f"карточка {card_id!r} содержит текст без числового x")
                    continue
                if (
                    text_element.get("text-anchor", "start") != "start"
                    or abs(x - box[0] - inset) > 1e-9
                ):
                    errors.append(
                        f"карточка {card_id!r}: ведущие строки должны быть выровнены слева "
                        "с отступом из architecture_diagram_template.svg"
                    )


def _point_on_rect_boundary(
    point: tuple[float, float], box: tuple[float, float, float, float]
) -> bool:
    x, y = point
    left, top, right, bottom = box
    on_horizontal = left <= x <= right and (abs(y - top) < 1e-9 or abs(y - bottom) < 1e-9)
    on_vertical = top <= y <= bottom and (abs(x - left) < 1e-9 or abs(x - right) < 1e-9)
    return on_horizontal or on_vertical


def _path_terminal_point(path_data: str) -> tuple[float, float] | None:
    """Return the last point of a simple absolute orthogonal SVG path."""

    x: float | None = None
    y: float | None = None
    segments = list(_PATH_SEGMENT.finditer(path_data))
    if not segments or "".join(match.group(0) for match in segments) != path_data.strip():
        return None
    for segment in segments:
        command = segment.group("command")
        if command != command.upper():
            return None
        values = [float(value) for value in _PATH_NUMBER.findall(segment.group("args"))]
        if command in {"M", "L"} and len(values) == 2:
            x, y = values
        elif command == "H" and len(values) == 1 and y is not None:
            x = values[0]
        elif command == "V" and len(values) == 1 and x is not None:
            y = values[0]
        else:
            return None
    if x is None or y is None:
        return None
    return x, y


def _measure_port_gaps(root_el, errors: list[str]) -> list[PortGap]:
    parents = {child: parent for parent in root_el.iter() for child in parent}
    by_id = {element.get("id"): element for element in root_el.iter() if element.get("id")}
    grouped: dict[str, list[tuple[str, str, tuple[float, float]]]] = {}
    for path in root_el.iter():
        group = path.get("data-port-group")
        if group is None:
            continue
        if _local_tag(path.tag) != "path":
            errors.append("data-port-group разрешён только для <path>")
            continue
        target_id = path.get("data-port-target")
        side = path.get("data-port-side")
        if not target_id or side not in {"left", "right"}:
            errors.append(
                f"портовая группа {group!r} обязана задать data-port-target и "
                "data-port-side='left'|'right'"
            )
            continue
        target = by_id.get(target_id)
        terminal = _path_terminal_point(path.get("d") or "")
        if target is None or _local_tag(target.tag) != "rect" or terminal is None:
            errors.append(
                f"портовая группа {group!r} не позволяет вычислить конечную точку "
                f"или прямоугольник {target_id!r}"
            )
            continue
        offset = _absolute_translation(
            path,
            parents,
            errors,
            contract="проверку интервала входных портов",
        )
        target_box = _absolute_rect_box(
            target,
            parents,
            errors,
            contract="проверку границы получателя портовой группы",
        )
        if offset is None or target_box is None:
            continue
        endpoint = terminal[0] + offset[0], terminal[1] + offset[1]
        expected_x = target_box[0] if side == "left" else target_box[2]
        if abs(endpoint[0] - expected_x) > 1e-9 or not (
            target_box[1] <= endpoint[1] <= target_box[3]
        ):
            errors.append(
                f"коннектор портовой группы {group!r} заканчивается в "
                f"({endpoint[0]:g}, {endpoint[1]:g}), не на {side}-границе "
                f"получателя {target_id!r}"
            )
            continue
        grouped.setdefault(group, []).append((target_id, side, endpoint))

    gaps: list[PortGap] = []
    for group, endpoints in grouped.items():
        if len(endpoints) != 2:
            errors.append(
                f"портовая группа {group!r} должна содержать ровно два коннектора, "
                f"фактически {len(endpoints)}"
            )
            continue
        targets = {(target_id, side) for target_id, side, _ in endpoints}
        if len(targets) != 1:
            errors.append(
                f"коннекторы портовой группы {group!r} должны входить в одну границу "
                "одного получателя"
            )
            continue
        target_id, side = targets.pop()
        gap = abs(endpoints[0][2][1] - endpoints[1][2][1])
        gaps.append(PortGap(group=group, target_id=target_id, side=side, value=gap))
    return gaps


def _check_reference_port_gaps(
    gaps: list[PortGap], reference_port_gap: float | None, errors: list[str]
) -> None:
    if reference_port_gap is None:
        return
    for gap in gaps:
        if abs(gap.value - reference_port_gap) > 1e-9:
            errors.append(
                f"интервал портовой группы {gap.group!r}: эталон шаблона "
                f"{reference_port_gap:g} px, фактически {gap.value:g} px"
            )


def _check_flow_label_layouts(
    root_el,
    errors: list[str],
    reference_layouts: dict[str, FlowLabelLayout] | None,
) -> list[FlowLabelLayout]:
    parents = {child: parent for parent in root_el.iter() for child in parent}
    texts_by_label: dict[str, list] = {}
    for element in root_el.iter():
        label_for = element.get("data-label-for")
        if label_for is not None:
            texts_by_label.setdefault(label_for, []).append(element)

    flow_plaques: list = []
    for plaque in root_el.iter():
        classes = set((plaque.get("class") or "").split())
        is_flow_plaque = bool(classes.intersection(_FLOW_LABEL_CLASSES))
        kind = plaque.get("data-layout")
        if not is_flow_plaque and kind not in _FLOW_LABEL_ROW_COUNTS:
            continue
        if _local_tag(plaque.tag) != "rect" or not is_flow_plaque:
            errors.append(
                'data-layout="flow-label*" разрешён только для <rect> класса '
                "flow-label/flow-label-*"
            )
            continue
        flow_plaques.append(plaque)

    plaque_ids = {plaque.get("id") for plaque in flow_plaques if plaque.get("id")}
    for label_for, labels in texts_by_label.items():
        if label_for not in plaque_ids:
            errors.append(
                f"data-label-for={label_for!r} не указывает на плашку класса flow-label-*"
            )

    layouts: list[FlowLabelLayout] = []
    widths_by_group: dict[str, list[tuple[str, float]]] = {}
    for plaque in flow_plaques:
        plaque_id = plaque.get("id")
        if not plaque_id:
            errors.append("каждая плашка класса flow-label/flow-label-* обязана иметь id")
            continue
        kind = plaque.get("data-layout")
        if kind not in _FLOW_LABEL_ROW_COUNTS:
            errors.append(
                f"плашка потока {plaque_id!r} обязана задать data-layout="
                "'flow-label' или 'flow-label-multiline'"
            )
            continue
        padding_profile = plaque.get("data-padding-profile")
        if padding_profile not in _FLOW_LABEL_PADDING_PROFILES:
            errors.append(
                f"плашка потока {plaque_id!r} обязана задать data-padding-profile="
                "'flow-caption' или 'flow-port'"
            )
        elif kind == "flow-label-multiline" and padding_profile != "flow-caption":
            errors.append(
                f"двухстрочная плашка потока {plaque_id!r} поддерживает только "
                "data-padding-profile='flow-caption'"
            )
        equal_width_group = plaque.get("data-equal-width-group")
        try:
            plaque_x = float(plaque.get("x", "0"))
            plaque_y = float(plaque.get("y", "0"))
            width = float(plaque.get("width"))
            height = float(plaque.get("height"))
            radius = float(plaque.get("rx"))
        except (TypeError, ValueError):
            errors.append(f"плашка потока {plaque_id!r} обязана иметь числовые x/y/width/height/rx")
            continue
        labels = texts_by_label.get(plaque_id, [])
        expected_rows = _FLOW_LABEL_ROW_COUNTS[kind]
        if len(labels) != expected_rows:
            errors.append(
                f"плашка потока {plaque_id!r} с data-layout={kind!r} должна иметь "
                f"ровно {expected_rows} <text data-label-for={plaque_id!r}>"
            )
            continue
        rows: list[tuple[float, str]] = []
        valid_rows = True
        for text_element in labels:
            if _local_tag(text_element.tag) != "text":
                errors.append(f"data-label-for={plaque_id!r} обязан стоять на <text>")
                valid_rows = False
                continue
            if parents.get(text_element) is not parents.get(plaque):
                errors.append(
                    f"подпись плашки {plaque_id!r} должна быть соседним элементом "
                    "того же контейнера"
                )
                valid_rows = False
                continue
            try:
                text_x = float(text_element.get("x"))
                text_y = float(text_element.get("y"))
            except (TypeError, ValueError):
                errors.append(f"подпись плашки {plaque_id!r} обязана иметь числовые x и y")
                valid_rows = False
                continue
            text_anchor = text_element.get("text-anchor", "start")
            expected_x = plaque_x + width / 2
            if text_anchor != "middle" or abs(text_x - expected_x) > 1e-9:
                errors.append(f"подпись плашки {plaque_id!r} обязана быть центрирована по ячейке")
            if padding_profile == "flow-caption":
                has_inline_segments = any(
                    _local_tag(child.tag) == "tspan" for child in text_element
                )
                if has_inline_segments:
                    errors.append(
                        f"flow-caption {plaque_id!r} не должна содержать <tspan>: "
                        "единый текстовый run обязателен для измерения естественной ширины"
                    )
                if text_element.get("data-width-anchor") is not None:
                    errors.append(
                        f"flow-caption {plaque_id!r} не должна задавать data-width-anchor: "
                        "ширина определяется естественной ink-рамкой самой широкой строки"
                    )
                if (
                    text_element.get("textLength") is not None
                    or text_element.get("lengthAdjust") is not None
                ):
                    errors.append(
                        f"flow-caption {plaque_id!r} не должна задавать "
                        "textLength/lengthAdjust: межбуквенный интервал должен оставаться естественным"
                    )
            elif padding_profile == "flow-port" and (
                text_element.get("textLength") is not None
                or text_element.get("lengthAdjust") is not None
                or text_element.get("data-width-anchor") is not None
            ):
                errors.append(
                    f"flow-port {plaque_id!r} не должен растягивать текст или задавать "
                    "якорь ширины: его ширину задаёт сетка родителя"
                )
            rows.append((text_y - plaque_y, text_anchor))
        if not valid_rows:
            continue
        rows.sort(key=lambda row: row[0])
        layouts.append(
            FlowLabelLayout(
                label_id=plaque_id,
                kind=kind,
                width=width,
                height=height,
                radius=radius,
                text_y_offsets=tuple(row[0] for row in rows),
                text_anchors=tuple(row[1] for row in rows),
            )
        )
        if equal_width_group:
            widths_by_group.setdefault(equal_width_group, []).append((plaque_id, width))

    layouts_by_kind: dict[str, list[FlowLabelLayout]] = {}
    for layout in layouts:
        layouts_by_kind.setdefault(layout.kind, []).append(layout)
    for kind, kind_layouts in layouts_by_kind.items():
        peer_signature = kind_layouts[0].signature()
        for layout in kind_layouts[1:]:
            if layout.signature() != peer_signature:
                errors.append(
                    f"геометрия плашки потока {layout.label_id!r} отличается от "
                    f"{kind_layouts[0].label_id!r}: строки и поля {kind!r} должны совпадать"
                )
    if reference_layouts is not None:
        for layout in layouts:
            reference_layout = reference_layouts.get(layout.kind)
            if reference_layout is None or layout.signature() != reference_layout.signature():
                errors.append(
                    f"геометрия плашки потока {layout.label_id!r} отличается от "
                    "эталона architecture_diagram_template.svg"
                )
    for group, members in widths_by_group.items():
        if len(members) < 2:
            errors.append(f"группа равной ширины {group!r} должна содержать минимум две плашки")
            continue
        reference_width = members[0][1]
        for label_id, width in members[1:]:
            if abs(width - reference_width) > 1e-9:
                errors.append(
                    f"ширина плашки {label_id!r} в группе {group!r}: "
                    f"эталон группы {reference_width:g} px, фактически {width:g} px"
                )
    return layouts


def _check_connector_source_attachment(root_el, errors: list[str]) -> None:
    parents = {child: parent for parent in root_el.iter() for child in parent}
    by_id = {element.get("id"): element for element in root_el.iter() if element.get("id")}
    for path in root_el.iter():
        source_ref = path.get("data-source-ref")
        if source_ref is None or _local_tag(path.tag) != "path":
            continue
        match = _PATH_START.match(path.get("d") or "")
        source = by_id.get(source_ref)
        if match is None or source is None or _local_tag(source.tag) != "rect":
            continue
        path_offset = _absolute_translation(
            path,
            parents,
            errors,
            contract="проверку начала исходящего коннектора",
        )
        source_box = _absolute_rect_box(
            source,
            parents,
            errors,
            contract="проверку границы источника коннектора",
        )
        if path_offset is None or source_box is None:
            continue
        start = (
            float(match.group("x")) + path_offset[0],
            float(match.group("y")) + path_offset[1],
        )
        if not _point_on_rect_boundary(start, source_box):
            errors.append(
                f"коннектор от {source_ref!r} начинается в точке "
                f"({start[0]:g}, {start[1]:g}), не на границе источника "
                f"({source_box[0]:g}, {source_box[1]:g})–"
                f"({source_box[2]:g}, {source_box[3]:g})"
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


def check_geometry(
    text: str,
    *,
    reference_gaps: dict[str, float] | None = None,
    reference_transition_layout: ControlTransitionLayout | None = None,
    reference_port_gap: float | None = None,
    reference_flow_label_layouts: dict[str, FlowLabelLayout] | None = None,
    reference_card_text_inset: float | None = None,
) -> GeometryResult:
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
    _check_reference_gaps(vertical_gaps, reference_gaps, errors)
    _check_declared_bottom_alignments(root_el, errors)
    _check_declared_center_alignments(root_el, errors)
    _check_centered_section_dividers(root_el, errors)
    _check_direct_routes(root_el, errors)
    _check_connector_source_attachment(root_el, errors)
    port_gaps = _measure_port_gaps(root_el, errors)
    _check_reference_port_gaps(port_gaps, reference_port_gap, errors)
    _check_shared_routes_stay_outside_cards(root_el, errors)
    if reference_card_text_inset is not None:
        _check_coloured_card_text_alignment(root_el, reference_card_text_inset, errors)
    control_transition_layouts = _check_control_transition_layouts(
        root_el, errors, reference_transition_layout
    )
    flow_label_layouts = _check_flow_label_layouts(root_el, errors, reference_flow_label_layouts)
    return GeometryResult(
        errors=errors,
        warnings=warnings,
        vertical_gaps=vertical_gaps,
        control_transition_layouts=control_transition_layouts,
        port_gaps=port_gaps,
        flow_label_layouts=flow_label_layouts,
    )


def measure_reference_flow_caption_padding(template_text: str) -> tuple[float | None, list[str]]:
    """Read `space-m` from the registered SVG template.

    The token is template data rather than a Python literal. Render lint
    applies it to natural text ink boxes; SVG text stretching is forbidden.
    """

    try:
        root_el = ElementTree.fromstring(template_text)
    except (ElementTree.ParseError, DefusedXmlException):
        return None, ["не удалось разобрать SVG-шаблон для токена space-m"]
    try:
        value = float(root_el.get("data-space-m"))
    except (TypeError, ValueError):
        return None, ["корневой <svg> шаблона обязан задать числовой data-space-m"]
    if value <= 0:
        return None, ["data-space-m шаблона обязан быть положительным"]
    return value, []
