from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from operations.scripts.traceability.generate_file_procedure_matrix import (
    collect_files,
    generate_file_procedure_matrix,
    generate_matrix,
    parse_yaml_frontmatter,
)


class ParseYamlFrontmatterTests(unittest.TestCase):
    def test_extracts_simple_fields(self) -> None:
        content = "---\nid: TASK_001\nwork_state: in-progress\n---\n\nBody\n"
        fields = parse_yaml_frontmatter(content)
        self.assertEqual(fields["id"], "TASK_001")
        self.assertEqual(fields["work_state"], "in-progress")

    def test_returns_empty_dict_without_frontmatter(self) -> None:
        self.assertEqual(parse_yaml_frontmatter("# Just a heading\n"), {})


class CollectFilesTests(unittest.TestCase):
    def _write_task(self, root: Path, task_id: str, tests: str = "") -> None:
        (root / "work" / "tasks").mkdir(parents=True, exist_ok=True)
        tests_line = f"tests: {tests}\n" if tests else ""
        (root / "work" / "tasks" / f"{task_id.lower()}.md").write_text(
            f"---\nid: {task_id}\nwork_state: in-progress\n{tests_line}---\n\nBody\n",
            encoding="utf-8",
        )

    def _write_test(self, root: Path, test_id: str, execution: str = "automated") -> None:
        (root / "work" / "tests").mkdir(parents=True, exist_ok=True)
        (root / "work" / "tests" / f"{test_id.lower()}.md").write_text(
            f"---\nid: {test_id}\nexecution: {execution}\n---\n\nBody\n",
            encoding="utf-8",
        )

    def test_collects_tasks_and_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_task(root, "TASK_001", tests="TEST_001")
            self._write_test(root, "TEST_001")

            files = collect_files(root)

            self.assertIn("TASK_001", files["tasks"])
            self.assertEqual(files["tasks"]["TASK_001"]["tests"], ["TEST_001"])
            self.assertIn("TEST_001", files["tests"])
            self.assertEqual(files["tests"]["TEST_001"]["execution"], "automated")

    def test_ignores_malformed_task_file_without_raising(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work" / "tasks").mkdir(parents=True)
            # No frontmatter id -> should simply be skipped, not raise.
            (root / "work" / "tasks" / "broken.md").write_text(
                "no frontmatter here", encoding="utf-8"
            )

            files = collect_files(root)

            self.assertEqual(files.get("tasks", {}), {})

    def test_collects_milestone_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work" / "m02").mkdir(parents=True)
            (root / "work" / "m02" / "final_report.md").write_text("x", encoding="utf-8")

            files = collect_files(root)

            self.assertIn("m02", files["milestones"])

    def test_empty_root_returns_empty_collections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            files = collect_files(Path(tmp))
            self.assertEqual(files, {})


class GenerateMatrixTests(unittest.TestCase):
    def test_includes_task_test_linkage_row(self) -> None:
        files = {
            "tasks": {
                "TASK_001": {"work_state": "in-progress", "tests": ["TEST_001"]},
            },
            "tests": {
                "TEST_001": {"execution": "automated"},
            },
        }
        matrix = generate_matrix(files)
        self.assertIn("| TASK_001 | in-progress | TEST_001 | automated | — |", matrix)

    def test_handles_task_without_tests(self) -> None:
        files = {"tasks": {"TASK_002": {"work_state": "planned", "tests": []}}, "tests": {}}
        matrix = generate_matrix(files)
        self.assertNotIn("TASK_002 |", matrix.split("## State Transition Timeline")[0])


class GenerateFileProcedureMatrixTests(unittest.TestCase):
    def test_writes_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertTrue(generate_file_procedure_matrix(root))

            output = root / "generated" / "file_procedure_traceability_matrix.md"
            self.assertTrue(output.exists())
            self.assertIn("do not edit manually", output.read_text(encoding="utf-8"))

    def test_returns_false_when_content_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            generate_file_procedure_matrix(root)
            # Second run against identical source state should be a no-op.
            self.assertFalse(generate_file_procedure_matrix(root))


if __name__ == "__main__":
    unittest.main()
