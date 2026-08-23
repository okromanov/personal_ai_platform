from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from operations.scripts.documents.owner_dashboard import (
    _coverage_stat,
    _document_family_counts,
    _lines_of_code,
    _step_timings,
    render_owner_dashboard,
)


class OwnerDashboardStatTests(unittest.TestCase):
    def test_lines_of_code_counts_only_files_under_the_given_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "a.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
            (root / "other").mkdir()
            (root / "other" / "b.py").write_text("z = 3\n", encoding="utf-8")

            import subprocess

            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)

            self.assertEqual(_lines_of_code(root, "src"), 2)
            self.assertEqual(_lines_of_code(root, "other"), 1)
            self.assertEqual(_lines_of_code(root, "missing"), 0)

    def test_document_family_counts_matches_headings_in_a_synthetic_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "specifications").mkdir()
            (root / "specifications" / "business_requirements.md").write_text(
                "### BR_001 — One\n### BR_002 — Two\n", encoding="utf-8"
            )
            (root / "specifications" / "system_specification.md").write_text(
                "### SYS_001 — Three\n", encoding="utf-8"
            )

            import subprocess

            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)

            counts = _document_family_counts(root)
            self.assertEqual(counts.get("BR"), 2)
            self.assertEqual(counts.get("SYS"), 1)

    def test_coverage_stat_reads_percent_and_timestamp_or_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(_coverage_stat(root))

            (root / "runtime").mkdir()
            (root / "runtime" / "coverage.json").write_text(
                json.dumps(
                    {
                        "meta": {"timestamp": "2026-08-23T20:39:24.759556"},
                        "totals": {"percent_covered_display": "84"},
                    }
                ),
                encoding="utf-8",
            )
            result = _coverage_stat(root)
            self.assertIsNotNone(result)
            assert result is not None
            percent, recorded_at = result
            self.assertEqual(percent, "84%")
            self.assertEqual(recorded_at, "2026-08-23 20:39:24")

    def test_step_timings_tolerates_missing_or_malformed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(_step_timings(root), {})

            (root / "runtime").mkdir()
            (root / "runtime" / "step_timings.json").write_text("not json", encoding="utf-8")
            self.assertEqual(_step_timings(root), {})

            (root / "runtime" / "step_timings.json").write_text(
                json.dumps({"Unit tests": 11.6, "bad": "nope"}), encoding="utf-8"
            )
            self.assertEqual(_step_timings(root), {"Unit tests": 11.6})


class OwnerDashboardRenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[3]

    def test_render_matches_tracked_file_and_covers_real_completed_task(self) -> None:
        # Unlike project_status.md/tasks.md/generated/*, owner_dashboard.md is
        # deliberately excluded from the byte-for-byte "generated drift" gate
        # (see run_suite.py's "Generated drift" step and check_generated() in
        # check.py): it embeds live wall-clock test/scan timing from
        # runtime/step_timings.json, which is real and reproducible-per-run but
        # not identical between two separate runs. So this test compares
        # everything except that one volatile table.
        rendered = render_owner_dashboard(self.root, "2026-08-23")
        tracked = (self.root / "owner_dashboard.md").read_text(encoding="utf-8-sig")
        marker = "## Статистика документов"
        self.assertEqual(tracked[tracked.index(marker) :], rendered[rendered.index(marker) :])

        for heading in [
            "## Статистика репозитория",
            "## Статистика документов",
            "## Что уже реализовано",
            "## Что уже может делать пользователь",
        ]:
            self.assertIn(heading, rendered)
        for removed_heading in ["## GitHub Actions", "## Ссылки на правила"]:
            self.assertNotIn(removed_heading, rendered)

        # TASK_001 is the one completed TASK in this repo; its Результат section
        # must actually surface here, not the auto_generate_tasks.py placeholder.
        self.assertIn("TASK_001", rendered)
        self.assertIn("TelegramChannel", rendered)
        self.assertNotIn(
            "полностью реализован, протестирован и интегрирован.",
            rendered,
        )

    def test_document_statistics_are_positive_not_hardcoded_placeholders(self) -> None:
        rendered = render_owner_dashboard(self.root, "2026-08-23")
        for label in ["Бизнес-требования", "Системные требования", "Проектные TASK"]:
            row = next(line for line in rendered.splitlines() if line.startswith(f"| {label} |"))
            count = int(row.split("`")[1])
            self.assertGreater(count, 0, row)


if __name__ == "__main__":
    unittest.main()
