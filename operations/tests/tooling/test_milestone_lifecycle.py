from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from operations.scripts.milestones.init_milestone import init_milestone
from operations.scripts.milestones.update_completion_report import (
    render_final_report,
    update_completion_report,
)


def _write_milestone_section(root: Path, milestone_id: str, work_state: str) -> None:
    (root / "milestones.md").write_text(
        f"## {milestone_id} — Тестовый этап\n\n- work_state: `{work_state}`\n",
        encoding="utf-8",
    )


def _install_template_contract(root: Path) -> None:
    source_root = Path(__file__).resolve().parents[3]
    (root / "operations/templates").mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_root / "operations/template_registry.json", root / "operations")
    shutil.copy2(
        source_root / "operations/templates/milestone_completion_report_template.md",
        root / "operations/templates",
    )


class InitMilestoneTests(unittest.TestCase):
    """render_final_report() needs milestones.md to already list the
    milestone (as start.py --apply would have set it before init_milestone.py
    runs), so every test here writes that section first."""

    def test_creates_only_final_report(self) -> None:
        """owner_checklist.md and semantic_review.md are deliberately not
        auto-generated: a per-milestone stub that only restates
        operations/acceptance.md and operations/semantic_review.md never
        accumulates content worth keeping (see init_milestone.py docstring)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _install_template_contract(root)
            _write_milestone_section(root, "m09", "in-progress")
            self.assertTrue(init_milestone("m09", root=root))

            report_path = root / "work" / "acceptance" / "m09_final_report.md"
            self.assertTrue(report_path.exists())
            self.assertFalse((root / "work" / "m09" / "owner_checklist.md").exists())
            self.assertFalse((root / "work" / "m09" / "semantic_review.md").exists())

    def test_final_report_frontmatter_references_milestone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _install_template_contract(root)
            _write_milestone_section(root, "m03", "in-progress")
            init_milestone("m03", root=root)

            report = (root / "work/acceptance/m03_final_report.md").read_text(encoding="utf-8")
            self.assertIn("id: m03_final_report", report)
            self.assertIn("milestone: m03", report)

    def test_final_report_starts_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _install_template_contract(root)
            _write_milestone_section(root, "m04", "in-progress")
            init_milestone("m04", root=root)

            report = (root / "work/acceptance/m04_final_report.md").read_text(encoding="utf-8")
            self.assertIn("completion_state: pending", report)
            self.assertIn("не применимо (TASK для этапа не создаются)", report)

    def test_does_not_overwrite_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _install_template_contract(root)
            _write_milestone_section(root, "m05", "in-progress")
            init_milestone("m05", root=root)
            report_path = root / "work/acceptance/m05_final_report.md"
            report_path.write_text("custom content", encoding="utf-8")

            init_milestone("m05", root=root)

            self.assertEqual(report_path.read_text(encoding="utf-8"), "custom content")

    def test_fails_when_milestone_missing_from_milestones_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _install_template_contract(root)
            (root / "milestones.md").write_text(
                "## m01 — Другой этап\n\n- work_state: `completed`\n", encoding="utf-8"
            )
            self.assertFalse(init_milestone("m20", root=root))
            self.assertFalse((root / "work/acceptance/m20_final_report.md").exists())


def _run_git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _run_git_output(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _init_repo(root: Path) -> None:
    _run_git(root, "init", "-q")
    _run_git(root, "config", "user.email", "test@example.com")
    _run_git(root, "config", "user.name", "Test")


class UpdateCompletionReportTests(unittest.TestCase):
    """render_final_report() reads real git history, so these tests build a
    small real repository rather than mocking every collect_* call."""

    def _make_repo(self, milestone_id: str) -> Path:
        tmp = tempfile.mkdtemp()
        root = Path(tmp)
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        _init_repo(root)
        _install_template_contract(root)
        _write_milestone_section(root, milestone_id, "in-progress")
        init_milestone(milestone_id, root=root)
        _run_git(root, "add", "-A")
        _run_git(root, "commit", "-q", "-m", "start milestone")
        return root

    def test_returns_false_when_report_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(update_completion_report("m07", root=root))

    def test_render_pending_milestone_stays_in_progress(self) -> None:
        root = self._make_repo("m06")

        rendered = render_final_report(root, "m06")

        self.assertIn("completion_state: pending", rendered)
        self.assertIn("- Статус: в процессе", rendered)
        self.assertIn("не применимо (TASK для этапа не создаются)", rendered)

    def test_marks_report_completed_at_the_completion_commit(self) -> None:
        root = self._make_repo("m06")
        (root / "extra_during_progress.txt").write_text("noise", encoding="utf-8")
        _run_git(root, "add", "-A")
        _run_git(root, "commit", "-q", "-m", "unrelated progress commit")

        _write_milestone_section(root, "m06", "completed")
        _run_git(root, "add", "-A")
        _run_git(root, "commit", "-q", "-m", "complete milestone")

        self.assertTrue(update_completion_report("m06", root=root))

        content = (root / "work/acceptance/m06_final_report.md").read_text(encoding="utf-8")
        self.assertIn("completion_state: completed", content)
        self.assertIn("- Статус: завершено", content)
        self.assertNotIn("Дата завершения: —", content)

    def test_refuses_to_render_when_completion_commit_is_a_shallow_boundary(self) -> None:
        """A shallow clone's boundary commit makes `git log`/`git show` look
        like nothing existed before it — the completion commit might really
        be earlier than local history reaches. render_final_report() must
        raise rather than silently trust that illusion (this is exactly what
        broke CI: work/acceptance/m01_final_report.md rendered with a fraction of its
        real content because a shallow checkout's boundary commit already
        showed m01 as completed)."""
        root = self._make_repo("m06")
        _write_milestone_section(root, "m06", "completed")
        _run_git(root, "add", "-A")
        _run_git(root, "commit", "-q", "-m", "complete milestone")
        completion_sha = _run_git_output(root, "rev-parse", "HEAD")
        (root / ".git" / "shallow").write_text(f"{completion_sha}\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "мелкий чекаут"):
            render_final_report(root, "m06")

    def test_returns_false_when_milestone_unknown(self) -> None:
        """final_report.md exists on disk but milestones.md has no matching
        section: render_final_report() raises, and update_completion_report()
        must report failure rather than write a broken file."""
        root = self._make_repo("m06")
        report_path = root / "work/acceptance/m10_final_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("placeholder", encoding="utf-8")

        self.assertFalse(update_completion_report("m10", root=root))
        self.assertEqual(report_path.read_text(encoding="utf-8"), "placeholder")


if __name__ == "__main__":
    unittest.main()
