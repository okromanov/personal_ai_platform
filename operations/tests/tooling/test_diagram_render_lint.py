from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from operations.scripts.documents import diagram_render_lint as render_lint
from operations.scripts.documents.diagram_render_lint import ElementBox


def _box(
    kind: str,
    cls: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    tag: str = "",
    anchor: str = "start",
    content: str = "",
) -> ElementBox:
    return ElementBox(
        kind=kind,
        tag=tag or ("rect" if kind == "shape" else "text"),
        cls=cls,
        anchor=anchor,
        content=content,
        x=x,
        y=y,
        w=w,
        h=h,
    )


def _canvas(w: float = 1000.0, h: float = 500.0) -> ElementBox:
    return ElementBox(
        kind="shape", tag="svg", cls="", anchor="", content="", x=0.0, y=0.0, w=w, h=h
    )


def _background_rect(canvas: ElementBox) -> ElementBox:
    """The `<rect width=... height=... fill="#FFFFFF"/>` every template
    draws behind everything else -- same size and origin as the canvas,
    but a distinct element with no class, exactly as the real templates
    emit it."""

    return _box("shape", "", canvas.x, canvas.y, canvas.w, canvas.h)


class CanvasBoxTests(unittest.TestCase):
    def test_reads_width_and_height_from_the_root_svg(self) -> None:
        canvas = render_lint._canvas_box(
            '<svg xmlns="http://www.w3.org/2000/svg" width="991" height="556"></svg>'
        )
        self.assertIsNotNone(canvas)
        assert canvas is not None
        self.assertEqual((canvas.w, canvas.h), (991.0, 556.0))

    def test_none_for_malformed_xml(self) -> None:
        self.assertIsNone(render_lint._canvas_box("<svg><unclosed></svg>"))

    def test_none_when_width_or_height_is_missing(self) -> None:
        self.assertIsNone(render_lint._canvas_box('<svg xmlns="http://www.w3.org/2000/svg"></svg>'))

    def test_none_when_width_or_height_is_not_numeric(self) -> None:
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="auto"></svg>'
        self.assertIsNone(render_lint._canvas_box(svg))


class ElementBoxTests(unittest.TestCase):
    def test_x1_y1_and_area_are_derived_from_origin_and_size(self) -> None:
        box = _box("shape", "card", 10.0, 20.0, 30.0, 40.0)
        self.assertEqual(box.x1, 40.0)
        self.assertEqual(box.y1, 60.0)
        self.assertEqual(box.area, 1200.0)


class IsCanvasShapeTests(unittest.TestCase):
    def test_matches_a_shape_at_the_same_origin_and_size_as_canvas(self) -> None:
        canvas = _canvas()
        background = _background_rect(canvas)
        self.assertTrue(render_lint._is_canvas_shape(background, canvas))

    def test_does_not_match_a_smaller_card(self) -> None:
        canvas = _canvas()
        card = _box("shape", "execution-card", 40.0, 140.0, 560.0, 180.0)
        self.assertFalse(render_lint._is_canvas_shape(card, canvas))

    def test_false_when_canvas_is_unknown(self) -> None:
        card = _box("shape", "execution-card", 40.0, 140.0, 560.0, 180.0)
        self.assertFalse(render_lint._is_canvas_shape(card, None))


class SmallestContainerTests(unittest.TestCase):
    def test_picks_the_smallest_shape_that_fully_contains_the_text(self) -> None:
        text = _box("text", "nested-title", 80.0, 240.0, 100.0, 16.0, content="Внутренний узел")
        outer = _box("shape", "execution-card", 40.0, 140.0, 560.0, 180.0)
        inner = _box("shape", "inner-card", 68.0, 236.0, 220.0, 40.0)
        container = render_lint._smallest_container(text, [outer, inner])
        self.assertIs(container, inner)

    def test_none_when_text_is_not_fully_inside_any_shape(self) -> None:
        text = _box("text", "component-title", 10.0, 100.0, 300.0, 20.0, content="Overflowing")
        card = _box("shape", "neutral-card", 20.0, 90.0, 200.0, 40.0)
        self.assertIsNone(render_lint._smallest_container(text, [card]))

    def test_containment_tolerance_absorbs_sub_pixel_rounding(self) -> None:
        text = _box("text", "flow-text", 100.0, 100.0, 50.0, 12.0, content="ARC_FLOW_001")
        # Card is 0.3px narrower than the text on each side -- sub-pixel
        # rounding noise from real getBBox() measurements, not a real defect.
        card = _box("shape", "flow-label", 100.3, 99.7, 49.4, 12.6)
        self.assertIsNotNone(render_lint._smallest_container(text, [card]))


class FindOverflowTests(unittest.TestCase):
    def test_no_error_when_text_fits_inside_its_container(self) -> None:
        text = _box("text", "component-title", 68.0, 176.0, 300.0, 22.0, content="Title")
        card = _box("shape", "execution-card", 40.0, 140.0, 560.0, 180.0)
        self.assertEqual(render_lint.find_overflow([text, card], _canvas()), [])

    def test_reports_overflow_into_the_shape_it_overlaps(self) -> None:
        """This is the real bug from the original process_diagram_template.svg:
        a centred component-title text 193px wide inside a 170px-wide card,
        overflowing by the same amount on each side."""

        card = _box("shape", "neutral-card", 660.0, 190.0, 170.0, 60.0)
        text = _box(
            "text",
            "component-title",
            648.6,
            199.0,
            192.9,
            21.0,
            anchor="middle",
            content="Результат: сохранён",
        )
        errors = render_lint.find_overflow([text, card], _canvas())
        self.assertEqual(len(errors), 1)
        self.assertIn("Результат: сохранён", errors[0])
        self.assertIn(".neutral-card", errors[0])

    def test_the_page_background_rect_does_not_mask_real_overflow(self) -> None:
        """Regression test for the bug caught while validating this module
        against the real (broken) template: the full-canvas background rect
        always fully contains any on-page text, so without excluding it,
        `_smallest_container` would silently accept it as a valid container
        for text that actually overflows its real card -- turning a real
        overflow into a false "everything fits" or, worse, a misleading
        "not centred against the page" report from the other check."""

        canvas = _canvas()
        background = _background_rect(canvas)
        card = _box("shape", "neutral-card", 660.0, 190.0, 170.0, 60.0)
        text = _box(
            "text",
            "component-title",
            648.6,
            199.0,
            192.9,
            21.0,
            anchor="middle",
            content="Результат: сохранён",
        )
        errors = render_lint.find_overflow([text, background, card], canvas)
        self.assertEqual(len(errors), 1)
        self.assertIn(".neutral-card", errors[0])

    def test_free_text_with_no_overlapping_shape_is_checked_against_canvas(self) -> None:
        canvas = _canvas(w=940.0, h=460.0)
        title = _box("text", "title", 40.0, 13.0, 500.0, 38.0, content="Page title")
        self.assertEqual(render_lint.find_overflow([title], canvas), [])

        overflowing_note = _box(
            "text", "template-note", 40.0, 438.0, 920.0, 12.0, content="Note that runs off the page"
        )
        errors = render_lint.find_overflow([overflowing_note], canvas)
        self.assertEqual(len(errors), 1)
        self.assertIn("холст", errors[0])

    def test_empty_text_content_is_ignored(self) -> None:
        card = _box("shape", "neutral-card", 0.0, 0.0, 10.0, 10.0)
        empty = _box("text", "component-title", 50.0, 50.0, 100.0, 20.0, content="")
        self.assertEqual(render_lint.find_overflow([empty, card], _canvas()), [])


class FindAsymmetricAnchorsTests(unittest.TestCase):
    def test_no_error_when_centred_within_tolerance(self) -> None:
        card = _box("shape", "flow-label", 250.0, 308.0, 140.0, 28.0)
        text = _box(
            "text", "flow-text", 254.0, 317.0, 132.0, 12.0, anchor="middle", content="ARC_FLOW_001"
        )
        self.assertEqual(render_lint.find_asymmetric_anchors([text, card], _canvas()), [])

    def test_reports_miscentred_text(self) -> None:
        card = _box("shape", "flow-label", 250.0, 308.0, 140.0, 28.0)
        text = _box(
            "text", "flow-text", 254.0, 317.0, 100.0, 12.0, anchor="middle", content="Off-centre"
        )
        errors = render_lint.find_asymmetric_anchors([text, card], _canvas())
        self.assertEqual(len(errors), 1)
        self.assertIn("Off-centre", errors[0])
        self.assertIn("не центрирован", errors[0])

    def test_left_anchored_text_is_never_flagged(self) -> None:
        card = _box("shape", "neutral-card", 40.0, 140.0, 560.0, 180.0)
        text = _box(
            "text",
            "component-text",
            68.0,
            205.0,
            400.0,
            18.0,
            anchor="start",
            content="Left aligned",
        )
        self.assertEqual(render_lint.find_asymmetric_anchors([text, card], _canvas()), [])

    def test_no_error_when_text_has_no_container(self) -> None:
        text = _box("text", "title", 40.0, 13.0, 300.0, 38.0, anchor="middle", content="Free text")
        self.assertEqual(render_lint.find_asymmetric_anchors([text], _canvas()), [])

    def test_page_background_is_excluded_as_a_container(self) -> None:
        """Without excluding the background rect, a text overflowing its
        real container symmetrically (equal padding on each side, just
        negative) would measure as perfectly "centred" against the page
        background and be reported as fine -- hiding the overflow instead
        of catching it under either check."""

        canvas = _canvas()
        background = _background_rect(canvas)
        text = _box(
            "text",
            "component-title",
            648.6,
            199.0,
            192.9,
            21.0,
            anchor="middle",
            content="Результат: сохранён",
        )
        self.assertEqual(render_lint.find_asymmetric_anchors([text, background], canvas), [])


class LintFileTests(unittest.TestCase):
    def test_lint_file_combines_overflow_and_anchor_errors_from_the_measurer(self) -> None:
        card = _box("shape", "neutral-card", 660.0, 190.0, 170.0, 60.0)
        label_card = _box("shape", "flow-label", 250.0, 308.0, 140.0, 28.0)
        overflowing = _box(
            "text",
            "component-title",
            648.6,
            199.0,
            192.9,
            21.0,
            anchor="middle",
            content="Результат: сохранён",
        )
        miscentred = _box(
            "text", "flow-text", 254.0, 317.0, 100.0, 12.0, anchor="middle", content="Off-centre"
        )
        canned = [card, label_card, overflowing, miscentred]

        def fake_measurer(_svg_text: str) -> list[ElementBox]:
            return canned

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svg = root / "diagram.svg"
            svg.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="500"></svg>',
                encoding="utf-8",
            )
            result = render_lint.lint_file(svg, root, measurer=fake_measurer)

        self.assertFalse(result.ok)
        self.assertEqual(result.file, "diagram.svg")
        self.assertEqual(len(result.errors), 2)
        self.assertTrue(any("Результат" in error for error in result.errors))
        self.assertTrue(any("Off-centre" in error for error in result.errors))

    def test_lint_file_passes_when_measurer_reports_no_defects(self) -> None:
        card = _box("shape", "execution-card", 40.0, 140.0, 560.0, 180.0)
        fine = _box("text", "component-title", 68.0, 176.0, 300.0, 22.0, content="Fine")

        def fake_measurer(_svg_text: str) -> list[ElementBox]:
            return [card, fine]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svg = root / "diagram.svg"
            svg.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="500"></svg>',
                encoding="utf-8",
            )
            result = render_lint.lint_file(svg, root, measurer=fake_measurer)

        self.assertTrue(result.ok)
        self.assertEqual(result.errors, [])

    def test_lint_file_tolerates_a_canvas_without_declared_dimensions(self) -> None:
        def fake_measurer(_svg_text: str) -> list[ElementBox]:
            return []

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svg = root / "diagram.svg"
            svg.write_text("<svg></svg>", encoding="utf-8")
            result = render_lint.lint_file(svg, root, measurer=fake_measurer)

        self.assertTrue(result.ok)


class MainCliTests(unittest.TestCase):
    def test_main_passes_an_explicit_clean_file(self) -> None:
        card = _box("shape", "execution-card", 40.0, 140.0, 560.0, 180.0)
        fine = _box("text", "component-title", 68.0, 176.0, 300.0, 22.0, content="Fine")

        def fake_measurer(_svg_text: str) -> list[ElementBox]:
            return [card, fine]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svg = root / "diagram.svg"
            svg.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="500"></svg>',
                encoding="utf-8",
            )
            with patch("sys.argv", ["diagram_render_lint.py", str(svg)]):
                exit_code = render_lint.main(measurer=fake_measurer)

        self.assertEqual(exit_code, 0)

    def test_main_fails_a_file_with_a_real_defect(self) -> None:
        card = _box("shape", "neutral-card", 660.0, 190.0, 170.0, 60.0)
        overflowing = _box(
            "text",
            "component-title",
            648.6,
            199.0,
            192.9,
            21.0,
            anchor="middle",
            content="Результат: сохранён",
        )

        def fake_measurer(_svg_text: str) -> list[ElementBox]:
            return [card, overflowing]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svg = root / "diagram.svg"
            svg.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="500"></svg>',
                encoding="utf-8",
            )
            with patch("sys.argv", ["diagram_render_lint.py", str(svg)]):
                exit_code = render_lint.main(measurer=fake_measurer)

        self.assertEqual(exit_code, 1)

    def test_main_reports_a_missing_file_without_invoking_the_measurer(self) -> None:
        calls: list[str] = []

        def fake_measurer(svg_text: str) -> list[ElementBox]:
            calls.append(svg_text)
            return []

        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.svg"
            with patch("sys.argv", ["diagram_render_lint.py", str(missing)]):
                exit_code = render_lint.main(measurer=fake_measurer)

        self.assertEqual(exit_code, 1)
        self.assertEqual(calls, [])

    def test_main_reports_no_targets_when_default_targets_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch("os.getcwd", return_value=tmp),
                patch(
                    "operations.scripts.documents.diagram_render_lint.find_project_root",
                    return_value=Path(tmp),
                ),
                patch(
                    "operations.scripts.documents.diagram_render_lint.default_targets",
                    return_value=[],
                ),
                patch("sys.argv", ["diagram_render_lint.py"]),
            ):
                exit_code = render_lint.main(measurer=lambda _svg_text: [])

        self.assertEqual(exit_code, 0)

    def test_main_delegates_to_diagram_lint_default_targets_when_no_paths_given(self) -> None:
        card = _box("shape", "execution-card", 0.0, 0.0, 10.0, 10.0)
        fine = _box("text", "component-title", 1.0, 1.0, 5.0, 5.0, content="Fine")

        def fake_measurer(_svg_text: str) -> list[ElementBox]:
            return [card, fine]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artefacts = root / "work" / "artefacts" / "architecture"
            artefacts.mkdir(parents=True)
            svg = artefacts / "diagram.svg"
            svg.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>',
                encoding="utf-8",
            )
            with (
                patch(
                    "operations.scripts.documents.diagram_render_lint.find_project_root",
                    return_value=root,
                ),
                patch("sys.argv", ["diagram_render_lint.py"]),
            ):
                exit_code = render_lint.main(measurer=fake_measurer)

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
