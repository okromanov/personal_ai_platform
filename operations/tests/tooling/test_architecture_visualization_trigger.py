from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from operations.scripts.common.project import run_command
from operations.scripts.tasks.check_architecture_visualization import (
    ARCHITECTURE_SVG,
    review_task_architecture_visualization,
)


class ArchitectureVisualizationTriggerTests(unittest.TestCase):
    def _commit(self, root: Path, message: str) -> str:
        self.assertTrue(run_command(["git", "add", "."], cwd=root).ok)
        self.assertTrue(run_command(["git", "commit", "-qm", message], cwd=root).ok)
        return run_command(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip()

    def _initialize(self, root: Path) -> None:
        self.assertTrue(run_command(["git", "init", "-q"], cwd=root).ok)
        self.assertTrue(run_command(["git", "config", "user.name", "Test"], cwd=root).ok)
        self.assertTrue(
            run_command(["git", "config", "user.email", "test@example.invalid"], cwd=root).ok
        )
        (root / "work/tasks").mkdir(parents=True)
        (root / "work/artefacts/architecture").mkdir(parents=True)
        (root / "specifications").mkdir()
        (root / "work/tasks/task_001_component.md").write_text(
            "---\nid: TASK_001\nwork_state: in-progress\n---\n\n# Task\n",
            encoding="utf-8",
        )
        (root / "specifications/architecture_baseline.md").write_text(
            '---\nversion: 1.0\n---\n\n<a id="arc_cmp_001"></a>\n'
            "### ARC_CMP_001 — Компонент\n\nИсходное описание.\n",
            encoding="utf-8",
        )
        for name in ("infrastructure_baseline.md", "system_specification.md"):
            (root / "specifications" / name).write_text(
                "---\nversion: 1.0\n---\n", encoding="utf-8"
            )
        (root / ARCHITECTURE_SVG).write_text(
            '<svg xmlns="http://www.w3.org/2000/svg">\n'
            "<!-- diagram-metadata\n"
            "diagram_id: architecture\n"
            "diagram_version: 1.0\n"
            "generated_at: 2026-09-10T00:00:00+00:00\n"
            "status: current\n"
            "source: specifications/architecture_baseline.md@1.0\n"
            "id: ARC_CMP_001\n"
            "end-diagram-metadata -->\n"
            '<text data-diagram-meta="version">Версия 1.0 · Обновлено '
            "2026-09-10 00:00 UTC</text>\n"
            '<text data-spec-id="ARC_CMP_001">Компонент</text>\n'
            "</svg>\n",
            encoding="utf-8",
        )

    def _complete_task(self, root: Path) -> None:
        task = root / "work/tasks/task_001_component.md"
        task.write_text(
            task.read_text(encoding="utf-8").replace("in-progress", "completed"),
            encoding="utf-8",
        )

    def _change_architecture(self, root: Path) -> None:
        source = root / "specifications/architecture_baseline.md"
        source.write_text(
            source.read_text(encoding="utf-8")
            .replace("version: 1.0", "version: 1.1")
            .replace("Исходное описание", "Новое описание"),
            encoding="utf-8",
        )

    def test_completed_task_without_architecture_change_needs_no_redraw(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._initialize(root)
            base = self._commit(root, "base")
            self._complete_task(root)
            head = self._commit(root, "complete")

            review = review_task_architecture_visualization(
                root, base, head, ["work/tasks/task_001_component.md"]
            )

            self.assertEqual(review.completed_tasks, ("TASK_001",))
            self.assertFalse(review.redraw_required)
            self.assertEqual(review.errors, ())

    def test_changed_visual_section_requires_real_svg_redraw(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._initialize(root)
            base = self._commit(root, "base")
            self._complete_task(root)
            self._change_architecture(root)
            head = self._commit(root, "complete with architecture change")
            changed = [
                "work/tasks/task_001_component.md",
                "specifications/architecture_baseline.md",
            ]

            missing = review_task_architecture_visualization(root, base, head, changed)

            self.assertEqual(missing.affected_ids, ("ARC_CMP_001",))
            self.assertTrue(any("не обновлён" in error for error in missing.errors))

            svg = root / ARCHITECTURE_SVG
            svg.write_text(
                svg.read_text(encoding="utf-8")
                .replace("diagram_version: 1.0", "diagram_version: 1.1")
                .replace("architecture_baseline.md@1.0", "architecture_baseline.md@1.1")
                .replace(
                    ">Компонент</text>",
                    ">Обновлённый компонент</text>",
                ),
                encoding="utf-8",
            )
            redrawn_head = self._commit(root, "redraw")
            updated = review_task_architecture_visualization(
                root, base, redrawn_head, [*changed, ARCHITECTURE_SVG]
            )

            self.assertTrue(updated.redraw_required)
            self.assertEqual(updated.errors, ())

    def test_metadata_only_update_is_not_a_redraw(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._initialize(root)
            base = self._commit(root, "base")
            self._complete_task(root)
            self._change_architecture(root)
            svg = root / ARCHITECTURE_SVG
            svg.write_text(
                svg.read_text(encoding="utf-8")
                .replace("diagram_version: 1.0", "diagram_version: 1.1")
                .replace("architecture_baseline.md@1.0", "architecture_baseline.md@1.1")
                .replace("Версия 1.0", "Версия 1.1"),
                encoding="utf-8",
            )
            head = self._commit(root, "metadata only")

            review = review_task_architecture_visualization(
                root,
                base,
                head,
                [
                    "work/tasks/task_001_component.md",
                    "specifications/architecture_baseline.md",
                    ARCHITECTURE_SVG,
                ],
            )

            self.assertTrue(any("только метаданные" in error for error in review.errors))
