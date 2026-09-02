"""Render-based checks for SVG diagrams: real text ink-boxes via headless
Chromium, matched against diagram_geometry_foundations.md §6/§9/§11.

Separate, deliberately optional tool -- not wired into diagram_lint.py,
check.py --all, or run_suite.py. It closes a gap those static checks are
honest about leaving open: diagram_geometry_lint.py's own module docstring
says text-overflow and label-plaque sizing are unautomatable "without
rendering the SVG or resolving an arbitrary transform stack ... requires
... real text metrics ... remain manual items on the checklist". This
module does exactly that rendering, at the cost of a dependency the
canonical toolchain does not carry: Playwright plus a downloaded Chromium
binary, which -- unlike every other pinned dev tool in
operations/quality/requirements_dev.txt -- is not `pip install
--require-hashes`-reproducible (the browser binary is a separate,
out-of-band download; see "Setup" below). Wiring this into the blocking
gate would mean adding that download to CI (network access, ~300 MB,
two more runners to provision) -- an infrastructure decision for the
repository owner, not one this tool makes for them by quietly appearing
in `check.py --all`.

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

What it deliberately does not check: contrast, readability at scaled-down
preview size, line-to-line crossings, exact geometric containment inside a
non-rectangular shape (a polygon's bounding box is used as its container,
which is a conservative approximation -- a diamond's corners are outside
its own bbox interior, so this can under-report overflow into a decision
node's corners). These remain manual items on the checklist
(diagram_geometry_foundations.md §17).

Setup (once; not part of the pinned toolchain)
------------------------------------------------
    python3.12 -m pip install playwright==<version>
    python3.12 -m playwright install chromium

Usage
-----
    python3.12 operations/scripts/documents/diagram_render_lint.py
    python3.12 operations/scripts/documents/diagram_render_lint.py <file.svg> ...

Default targets are the same as diagram_lint.py's (work/artefacts/**/*.svg
plus operations/architecture/templates/*.svg).

Testability
-----------
`measure_svg_elements` is the one function in this module that launches a
browser; it is not exercised by the automated test suite (no Chromium
binary is guaranteed present wherever tests run, and this repository's
"no skipped tests" policy -- operations/scripts/quality/run_unittests.py
-- forbids a test that quietly no-ops when a dependency is missing).
Every other function -- `find_overflow`, `find_asymmetric_anchors`,
`lint_file`, `main` -- takes or defaults to a `measurer` callable, so
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

_ANCHOR_TOLERANCE_PX = 2.0
_CONTAINMENT_TOLERANCE_PX = 0.5  # sub-pixel rounding slack for "fully inside"

_MEASURE_JS = """() => {
  const box = (el, kind) => {
    const b = el.getBBox();
    const m = el.getCTM();
    return {
      kind,
      tag: el.tagName.toLowerCase(),
      cls: el.getAttribute('class') || '',
      anchor: el.getAttribute('text-anchor') || 'start',
      content: (el.textContent || '').trim(),
      x: b.x + (m ? m.e : 0),
      y: b.y + (m ? m.f : 0),
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

    from playwright.sync_api import sync_playwright  # local import: optional heavy dependency

    with sync_playwright() as playwright:
        browser = (
            playwright.chromium.launch(executable_path=executable_path)
            if executable_path
            else playwright.chromium.launch()
        )
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
    return result


def main(*, measurer: Measurer = measure_svg_elements) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Рендер-проверка SVG-схем через headless Chromium: переполнение текста "
            "за границы объектов, несимметричные поля центрированных подписей. "
            "Требует Playwright + Chromium (см. docstring модуля); не входит в "
            "check.py --all и run_suite.py."
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
