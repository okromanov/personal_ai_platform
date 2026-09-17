"""Render-based checks for SVG diagrams: real text ink-boxes via headless
Chromium, matched against diagram_geometry_foundations.md §6/§9/§10.

This is the rendered-geometry step of the canonical full quality suite.
Static XML can prove that a text anchor sits on a rectangle's centre, but
cannot prove the visible glyphs have the programmed padding: font metrics,
side bearings and transforms only exist after rendering. This module closes
that gap and makes padding profiles executable rather than advisory prose.

What it checks, precisely
--------------------------
1. **Text overflow** (`find_overflow`): every `<text>` element's real,
   post-transform ink box (`getBBox()` + the accumulated CTM -- so this is
   exactly what a reader would see, not a font-metrics estimate) must fit
   inside its smallest enclosing shape (`<rect>`/`<polygon>`/`<circle>`/
   `<ellipse>`), or -- for header/footer text with no enclosing shape at
   all -- inside the canvas.
2. **Anchor symmetry** (`find_asymmetric_anchors`): a `text-anchor="middle"`
   label's left and right padding against its smallest enclosing shape
   must match within `_ANCHOR_TOLERANCE_PX` (foundations §11: "плашка и
   текст имеют общий геометрический центр").
3. **Programmed padding profiles** (`find_padding_violations`): every shape
   with `data-padding-profile` is checked against the profile selected by
   its object type. `flow-caption` requires compact `space-m` padding around
   the widest row; `flow-port` keeps a fixed cell but still requires at least
   `space-m` and symmetric visible fields.

What it deliberately does not check: contrast, readability at scaled-down
preview size, line-to-line crossings, exact geometric containment inside a
non-rectangular shape (a polygon's bounding box is used as its container,
which is a conservative approximation -- a diamond's corners are outside
its own bbox interior, so this can under-report overflow into a decision
node's corners). These remain manual items on the checklist
(diagram_geometry_foundations.md §17).

Runtime
-------
Playwright is pinned in `requirements_dev.txt`. The measurer first uses the
system Chrome channel available on the canonical CI runner, then falls back
to a Playwright-managed Chromium installation.

Usage
-----
    python3.12 operations/scripts/documents/diagram_render_lint.py
    python3.12 operations/scripts/documents/diagram_render_lint.py <file.svg> ...

Default targets are the same as diagram_lint.py's (work/artefacts/**/*.svg
plus operations/architecture/templates/*.svg).

Testability
-----------
`measure_svg_elements` is the one function in this module that launches a
browser. Every other function -- `find_overflow`,
`find_asymmetric_anchors`, `find_padding_violations`, `lint_file`, `main` --
takes or defaults to a `measurer` callable, so
test_diagram_render_lint.py exercises the real checking logic and the real
CLI against a fake, in-process measurer with canned `ElementBox` lists,
with zero external dependencies. Run this module directly against real
files (see Usage) to exercise the browser path itself.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
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
from operations.scripts.documents.diagram_lint import default_targets

_ANCHOR_TOLERANCE_PX = 1.0
_CONTAINMENT_TOLERANCE_PX = 0.5  # sub-pixel rounding slack for "fully inside"
_PADDING_TOLERANCE_PX = 0.5
_FLOW_LABEL_CLASSES = {
    "flow-label",
    "flow-label-blue",
    "flow-label-gray",
    "flow-label-green",
    "flow-label-red",
}
_PADDING_PROFILES = {
    # Content-sized label: width is the widest rendered row plus 2*space-m,
    # rounded up by at most one 4 px grid step. Per-side padding is therefore
    # 12 <= p < 14 px before the small render tolerance is applied.
    "flow-caption": (12.0, 14.0),
    # Fixed-width port cell: only the minimum and symmetry are normative.
    "flow-port": (12.0, None),
}

_MEASURE_JS = """() => {
  const box = (el, kind) => {
    const b = el.getBoundingClientRect();
    return {
      kind,
      tag: el.tagName.toLowerCase(),
      id: el.getAttribute('id') || '',
      cls: el.getAttribute('class') || '',
      anchor: el.getAttribute('text-anchor') || 'start',
      content: (el.textContent || '').trim(),
      label_for: el.getAttribute('data-label-for') || '',
      padding_profile: el.getAttribute('data-padding-profile') || '',
      equal_width_group: el.getAttribute('data-equal-width-group') || '',
      x: b.x,
      y: b.y,
      w: b.width,
      h: b.height,
    };
  };
  const texts = Array.from(document.querySelectorAll('text')).map((el) => box(el, 'text'));
  const shapes = Array.from(document.querySelectorAll('rect, polygon, circle, ellipse'))
    .map((el) => box(el, 'shape'));
  return texts.concat(shapes);
}"""


@dataclass(frozen=True)
class ElementBox:
    """One element's real ink box in final document coordinates (post-CTM)."""

    kind: str  # "text" | "shape"
    tag: str
    cls: str
    anchor: str
    content: str
    x: float
    y: float
    w: float
    h: float
    id: str = ""
    label_for: str = ""
    padding_profile: str = ""
    equal_width_group: str = ""

    @property
    def x1(self) -> float:
        return self.x + self.w

    @property
    def y1(self) -> float:
        return self.y + self.h

    @property
    def area(self) -> float:
        return self.w * self.h


@dataclass
class LintResult:
    file: str
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


Measurer = Callable[[str], list[ElementBox]]


def measure_svg_elements(svg_text: str, *, executable_path: str | None = None) -> list[ElementBox]:
    """Render `svg_text` in headless Chromium and return every `<text>` and
    measurable shape element's real ink box. See the module docstring's
    "Testability" section for why this function has no automated test.
    """

    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        if executable_path:
            browser = playwright.chromium.launch(executable_path=executable_path)
        else:
            try:
                browser = playwright.chromium.launch(channel="chrome")
            except PlaywrightError:
                browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(f"<!doctype html><body style='margin:0'>{svg_text}</body>")
            page.evaluate(
                "document.fonts.ready"
            )  # wait for the real fallback font, not a fixed sleep
            raw = page.evaluate(_MEASURE_JS)
        finally:
            browser.close()
    return [ElementBox(**item) for item in raw]


def _canvas_box(svg_text: str) -> ElementBox | None:
    try:
        root_el = ElementTree.fromstring(svg_text)
    except (ElementTree.ParseError, DefusedXmlException):
        return None
    width, height = root_el.get("width"), root_el.get("height")
    if width is None or height is None:
        return None
    try:
        return ElementBox(
            kind="shape",
            tag="svg",
            cls="",
            anchor="",
            content="",
            x=0.0,
            y=0.0,
            w=float(width),
            h=float(height),
        )
    except ValueError:
        return None


def _is_canvas_shape(
    shape: ElementBox, canvas: ElementBox | None, *, tolerance: float = _CONTAINMENT_TOLERANCE_PX
) -> bool:
    """True for the full-page background rect every template draws
    (`<rect width=... height=... fill="#FFFFFF"/>`, no class). Without this
    exclusion it silently qualifies as a valid "container" for any
    overflowing text -- being exactly canvas-sized, it always fully
    contains everything on the page -- which turns a real overflow into a
    nonsensical false "not centred against the page background" report
    instead of the correct overflow error. Overflow onto the bare canvas
    already has its own check (the `canvas` fallback branch in
    find_overflow); this only removes the background rect from the
    container *candidate* list, it does not skip checking that text.
    """

    return (
        canvas is not None
        and abs(shape.x - canvas.x) <= tolerance
        and abs(shape.y - canvas.y) <= tolerance
        and abs(shape.w - canvas.w) <= tolerance
        and abs(shape.h - canvas.h) <= tolerance
    )


def _smallest_container(
    text: ElementBox, shapes: list[ElementBox], *, tolerance: float = _CONTAINMENT_TOLERANCE_PX
) -> ElementBox | None:
    candidates = [
        shape
        for shape in shapes
        if shape.x - tolerance <= text.x
        and shape.y - tolerance <= text.y
        and shape.x1 + tolerance >= text.x1
        and shape.y1 + tolerance >= text.y1
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda shape: shape.area)


def _overlapping_shapes(text: ElementBox, shapes: list[ElementBox]) -> list[ElementBox]:
    return [
        shape
        for shape in shapes
        if not (text.x1 < shape.x or text.x > shape.x1 or text.y1 < shape.y or text.y > shape.y1)
    ]


def find_overflow(elements: list[ElementBox], canvas: ElementBox | None) -> list[str]:
    """Text not fully contained by its smallest enclosing shape -- the
    visible defect this tool exists to catch ('текст вылазит за границы
    объектов'). A shape it partially overlaps but does not fit inside is
    named directly; free-floating text (no overlapping shape at all, e.g.
    a page title) is checked against the canvas instead.
    """

    shapes = [
        element
        for element in elements
        if element.kind == "shape" and not _is_canvas_shape(element, canvas)
    ]
    errors: list[str] = []
    for text in (element for element in elements if element.kind == "text" and element.content):
        if _smallest_container(text, shapes) is not None:
            continue
        overlapping = _overlapping_shapes(text, shapes)
        if overlapping:
            target = min(overlapping, key=lambda shape: shape.area)
            errors.append(
                f'текст "{text.content[:40]}" (.{text.cls or "?"}) выходит за границы '
                f".{target.cls or target.tag}"
            )
            continue
        if canvas is not None and (
            text.x < -_CONTAINMENT_TOLERANCE_PX
            or text.y < -_CONTAINMENT_TOLERANCE_PX
            or text.x1 > canvas.w + _CONTAINMENT_TOLERANCE_PX
            or text.y1 > canvas.h + _CONTAINMENT_TOLERANCE_PX
        ):
            errors.append(
                f'текст "{text.content[:40]}" (.{text.cls or "?"}) выходит за пределы холста'
            )
    return errors


def find_asymmetric_anchors(
    elements: list[ElementBox],
    canvas: ElementBox | None,
    *,
    tolerance: float = _ANCHOR_TOLERANCE_PX,
) -> list[str]:
    """A `text-anchor="middle"` label is meant to sit centred on its
    container (foundations §11: "плашка и текст имеют общий геометрический
    центр... ручное смещение текста для компенсации неравных полей
    запрещено"). A left/right padding mismatch beyond `tolerance` is that
    forbidden manual offset, caught by measurement instead of by eye.

    `canvas` excludes the full-page background rect from the container
    candidates (see `_is_canvas_shape`) -- without that exclusion, text
    that overflows its real container on both sides symmetrically would
    still measure as "centred" against the page background, silently
    hiding exactly the overflow `find_overflow` exists to catch.
    """

    shapes = [
        element
        for element in elements
        if element.kind == "shape" and not _is_canvas_shape(element, canvas)
    ]
    errors: list[str] = []
    for text in (
        element
        for element in elements
        if element.kind == "text" and element.anchor == "middle" and element.content
    ):
        container = _smallest_container(text, shapes)
        if container is None:
            continue
        left = text.x - container.x
        right = container.x1 - text.x1
        if abs(left - right) > tolerance:
            errors.append(
                f'текст "{text.content[:40]}" (.{text.cls or "?"}) не центрирован в '
                f".{container.cls or container.tag}: слева {left:.1f}px, справа {right:.1f}px"
            )
    return errors


def _inline_edges(box: ElementBox, *, vertical: bool) -> tuple[float, float, float]:
    if vertical:
        return box.y, box.y1, box.h
    return box.x, box.x1, box.w


def find_padding_violations(elements: list[ElementBox]) -> list[str]:
    """Check rendered ink padding selected by each object's padding profile.

    Flow captions are content-sized, so the widest row (or the widest row of
    an explicitly equal-width group) must leave `space-m` plus at most half of
    one 4 px rounding step on either side. Port cells are fixed by their parent
    grid and therefore only enforce the minimum field.
    Every row is checked for visible leading/trailing symmetry after transforms.
    """

    texts_by_label: dict[str, list[ElementBox]] = {}
    for element in elements:
        if element.kind == "text" and element.label_for:
            texts_by_label.setdefault(element.label_for, []).append(element)

    errors: list[str] = []
    grouped_captions: dict[str, list[tuple[str, float, float]]] = {}
    for plaque in (
        element
        for element in elements
        if element.kind == "shape" and element.padding_profile
    ):
        if plaque.w == 0 or plaque.h == 0:
            # Geometry references inside <defs> are intentionally not rendered.
            continue
        profile = _PADDING_PROFILES.get(plaque.padding_profile)
        if profile is None:
            errors.append(
                f"плашка {plaque.id or '<без id>'!r} использует неизвестный "
                f"padding-профиль {plaque.padding_profile!r}"
            )
            continue
        if not set(plaque.cls.split()).intersection(_FLOW_LABEL_CLASSES):
            errors.append(
                f"padding-профиль {plaque.padding_profile!r} назначен неподдерживаемому "
                f"объекту {plaque.id or '<без id>'!r}"
            )
            continue
        rows = texts_by_label.get(plaque.id, [])
        if not rows:
            errors.append(
                f"плашка {plaque.id or '<без id>'!r} не имеет измеряемой строки data-label-for"
            )
            continue

        vertical = plaque.h > plaque.w
        plaque_start, plaque_end, plaque_inline = _inline_edges(plaque, vertical=vertical)
        widest_inline = 0.0
        smallest_side = float("inf")
        for row in rows:
            row_start, row_end, row_inline = _inline_edges(row, vertical=vertical)
            leading = row_start - plaque_start
            trailing = plaque_end - row_end
            widest_inline = max(widest_inline, row_inline)
            smallest_side = min(smallest_side, leading, trailing)
            if abs(leading - trailing) > _ANCHOR_TOLERANCE_PX:
                errors.append(
                    f'строка "{row.content[:40]}" в {plaque.id!r} имеет несимметричные '
                    f"поля: первое {leading:.1f}px, второе {trailing:.1f}px"
                )

        minimum, maximum = profile
        if smallest_side < minimum - _PADDING_TOLERANCE_PX:
            errors.append(
                f"плашка {plaque.id!r} нарушает минимальный padding профиля "
                f"{plaque.padding_profile!r}: {smallest_side:.1f}px < {minimum:.1f}px"
            )
        average_widest_padding = (plaque_inline - widest_inline) / 2
        if maximum is not None and plaque.equal_width_group:
            grouped_captions.setdefault(plaque.equal_width_group, []).append(
                (plaque.id, plaque_inline, widest_inline)
            )
        elif maximum is not None and average_widest_padding >= maximum + _PADDING_TOLERANCE_PX:
            errors.append(
                f"плашка {plaque.id!r} некомпактна для профиля "
                f"{plaque.padding_profile!r}: поле {average_widest_padding:.1f}px, "
                f"допустимо < {maximum:.1f}px"
            )
    for group, members in grouped_captions.items():
        group_inline = min(member[1] for member in members)
        group_widest = max(member[2] for member in members)
        group_padding = (group_inline - group_widest) / 2
        maximum = _PADDING_PROFILES["flow-caption"][1]
        assert maximum is not None
        if group_padding >= maximum + _PADDING_TOLERANCE_PX:
            errors.append(
                f"группа равной ширины {group!r} некомпактна для профиля "
                f"'flow-caption': поле по самой широкой строке группы "
                f"{group_padding:.1f}px, допустимо < {maximum:.1f}px"
            )
    return errors


def _display_name(path: Path, root: Path) -> str:
    try:
        return relative_posix(path, root)
    except ValueError:
        return str(path)


def lint_file(path: Path, root: Path, *, measurer: Measurer = measure_svg_elements) -> LintResult:
    text = read_text(path)
    result = LintResult(file=_display_name(path, root))
    elements = measurer(text)
    canvas = _canvas_box(text)
    result.errors.extend(find_overflow(elements, canvas))
    result.errors.extend(find_asymmetric_anchors(elements, canvas))
    result.errors.extend(find_padding_violations(elements))
    return result


def main(*, measurer: Measurer = measure_svg_elements) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Рендер-проверка SVG-схем через headless Chromium: переполнение текста "
            "за границы объектов, несимметричные поля и программные padding-профили. "
            "Требует Playwright и Chrome/Chromium; входит в полный quality gate."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Файлы .svg для проверки. По умолчанию — те же цели, что у diagram_lint.py.",
    )
    args = parser.parse_args()
    require_supported_python()
    root = find_project_root(Path.cwd())

    targets = [p if p.is_absolute() else Path.cwd() / p for p in args.paths] or default_targets(
        root
    )
    if not targets:
        print("Файлы схем не найдены — проверять нечего.")
        return 0

    all_ok = True
    total_errors = 0
    for target in targets:
        if not target.is_file():
            print(f"[FAIL] {target}")
            print(f"  ERROR: файл не найден: {target}")
            all_ok = False
            total_errors += 1
            continue
        result = lint_file(target, root, measurer=measurer)
        print(f"[{'PASS' if result.ok else 'FAIL'}] {result.file}")
        for error in result.errors:
            print(f"  ERROR: {error}")
        all_ok = all_ok and result.ok
        total_errors += len(result.errors)

    print(f"Итог: файлов={len(targets)}, errors={total_errors}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
