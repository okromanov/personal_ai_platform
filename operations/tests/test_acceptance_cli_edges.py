from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from operations.scripts.acceptance import apply
from operations.scripts.common.project import CommandResult


class AcceptanceHelperEdgeTests(unittest.TestCase):
    def test_evidence_and_semantic_inputs_fail_closed_at_schema_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "input.json"
            with patch.object(apply, "_require_clean_worktree"):
                path.write_text("{", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "not valid JSON"):
                    apply.validate_evidence_bundle(root, path, "m02")
                path.write_text("[]", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "JSON object"):
                    apply.validate_evidence_bundle(root, path, "m02")
                for data, message in [
                    ({"schema_version": 2, "milestone": "m03"}, "другому milestone"),
                    (
                        {"schema_version": 2, "milestone": "m02", "acceptance_state": "blocked"},
                        "техническую готовность",
                    ),
                    (
                        {
                            "schema_version": 2,
                            "milestone": "m02",
                            "acceptance_state": "ready-for-semantic-review",
                            "pending_gates": ["semantic_review"],
                            "blockers": ["failure"],
                        },
                        "blockers",
                    ),
                ]:
                    path.write_text(json.dumps(data), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, message):
                        apply.validate_evidence_bundle(root, path, "m02")

            path.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not valid JSON"):
                apply.validate_semantic_review(root, path, "m02")
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON object"):
                apply.validate_semantic_review(root, path, "m02")
            for semantic_data, message in [
                ({"type": "wrong", "milestone": "m02"}, "type/milestone"),
                (
                    {"type": "semantic_review", "milestone": "m02", "result": "fail"},
                    "PASS",
                ),
            ]:
                path.write_text(json.dumps(semantic_data), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    apply.validate_semantic_review(root, path, "m02")

    def test_scope_fallback_and_invalid_canonical_lists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "specifications").mkdir()
            (root / "milestones.md").write_text("No explicit scope\n", encoding="utf-8")
            (root / "specifications/business_requirements.md").write_text(
                "### BR_002 — Later\n- priority: `candidate`\n"
                "### BR_001 — Core\n- priority: `core`\n",
                encoding="utf-8",
            )
            self.assertEqual(apply.canonical_v1_scope_ids(root), ["BR_001"])

            (root / "milestones.md").write_text(
                "Обязательный состав продукта: none\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "пуст"):
                apply.canonical_v1_scope_ids(root)
            (root / "milestones.md").write_text(
                "Обязательный состав продукта: BR_001, BR_001\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "повторные"):
                apply.canonical_v1_scope_ids(root)

    def test_typed_state_helpers_reject_malformed_or_illegal_transitions(self) -> None:
        with self.assertRaisesRegex(ValueError, "front matter"):
            apply._replace_front_matter_state(
                "body", field="decision_state", allowed_from={"proposed"}, target="accepted"
            )
        with self.assertRaisesRegex(ValueError, "Некорректный"):
            apply._replace_front_matter_state(
                "---\ndecision_state: proposed\n",
                field="decision_state",
                allowed_from={"proposed"},
                target="accepted",
            )
        with self.assertRaisesRegex(ValueError, "не содержит"):
            apply._replace_front_matter_state(
                "---\nid: x\n---\n",
                field="decision_state",
                allowed_from={"proposed"},
                target="accepted",
            )
        with self.assertRaisesRegex(ValueError, "Недопустимый"):
            apply._replace_front_matter_state(
                "---\ndecision_state: obsolete\n---\n",
                field="decision_state",
                allowed_from={"proposed"},
                target="accepted",
            )
        unchanged = apply._replace_front_matter_state(
            "---\ndecision_state: accepted\n---\n",
            field="decision_state",
            allowed_from={"proposed"},
            target="accepted",
        )
        self.assertIn("accepted", unchanged)
        with self.assertRaisesRegex(ValueError, "updated"):
            apply._replace_front_matter_state(
                "---\ndecision_state: proposed\n---\n",
                field="decision_state",
                allowed_from={"proposed"},
                target="accepted",
                updated="2026-08-21",
            )

        with self.assertRaisesRegex(ValueError, "Некорректный"):
            apply._replace_front_matter_updated("---\nupdated: 2026-08-20\n", "2026-08-21")
        with self.assertRaisesRegex(ValueError, "updated"):
            apply._replace_front_matter_updated("---\nid: x\n---\n", "2026-08-21")

        with self.assertRaisesRegex(ValueError, "отсутствует work_state"):
            apply._replace_milestone_work_state("## m02 — X\n", "m02")
        with self.assertRaisesRegex(ValueError, "недопустимый переход"):
            apply._replace_milestone_work_state("## m02 — X\n- work_state: `planned`\n", "m02")
        self.assertIn(
            "completed",
            apply._replace_milestone_work_state("## m02 — X\n- work_state: `completed`\n", "m02"),
        )
        with self.assertRaisesRegex(ValueError, "Не найден milestone"):
            apply._replace_milestone_work_state("## m02 — X\n- work_state: `planned`\n", "m03")

    def test_file_digest_is_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "artifact.txt"
            path.write_bytes(b"evidence")
            self.assertEqual(
                apply._file_sha256(path),
                "ee8250fb76e094b34b471f13a73dbbe51d1ae142e9df59d7c0d31ec20f0a0a8e",
            )

    def test_git_helpers_and_clean_tree_fail_closed(self) -> None:
        failure = CommandResult(("git",), 1, "", "error")
        dirty = CommandResult(("git",), 0, " M file", "")
        success = CommandResult(("git",), 0, "value\n", "")
        with patch.object(apply, "run_command", return_value=failure):
            with self.assertRaises(ValueError):
                apply._git_head(Path("."))
            with self.assertRaises(ValueError):
                apply._git_branch(Path("."))
            with self.assertRaises(ValueError):
                apply._require_clean_worktree(Path("."))
        with patch.object(apply, "run_command", return_value=dirty):
            with self.assertRaisesRegex(ValueError, "незакоммиченные"):
                apply._require_clean_worktree(Path("."))
        with patch.object(apply, "run_command", return_value=success):
            self.assertEqual(apply._git_head(Path(".")), "value")
            self.assertEqual(apply._git_branch(Path(".")), "value")
        clean = CommandResult(("git",), 0, "", "")
        with patch.object(apply, "run_command", return_value=clean):
            apply._require_clean_worktree(Path("."))


class AcceptanceCliTests(unittest.TestCase):
    def _arguments(self, root: Path, *, semantic: bool = True) -> list[str]:
        evidence = root / "evidence.json"
        semantic_path = root / "semantic.json"
        evidence.write_text("{}", encoding="utf-8")
        semantic_path.write_text("{}", encoding="utf-8")
        result = [
            "acceptance",
            "--milestone",
            "m02",
            "--owner-confirmation",
            "ПРИНИМАЮ m02",
            "--evidence",
            str(evidence),
            "--evidence-run-url",
            "https://github.com/example/repo/actions/runs/1",
            "--evidence-run-id",
            "1",
            "--evidence-repository",
            "example/repo",
            "--evidence-workflow",
            "Project check",
            "--evidence-event-sha",
            "a" * 40,
            "--evidence-artifact-id",
            "42",
            "--evidence-artifact-digest",
            "b" * 64,
        ]
        if semantic:
            result.extend(["--semantic-review", str(semantic_path)])
        return result

    def test_main_prepares_transition_and_server_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._arguments(root)
            evidence = {
                "git_sha": "a" * 40,
                "server_source": {
                    "repository": "example/repo",
                    "workflow": "Project check",
                    "run_id": "1",
                    "run_url": "https://github.com/example/repo/actions/runs/1",
                    "event_sha": "a" * 40,
                },
            }
            semantic = {"result": "pass"}
            with (
                patch("sys.argv", args),
                patch.object(apply, "require_supported_python"),
                patch.object(apply, "find_project_root", return_value=root),
                patch.object(apply, "_git_branch", return_value="feature"),
                patch.object(apply, "validate_evidence_bundle", return_value=evidence),
                patch.object(apply, "validate_semantic_review", return_value=semantic),
                patch.object(apply, "_file_sha256", side_effect=["1" * 64, "2" * 64]),
                patch.object(apply, "now_iso_minutes", return_value="2026-08-20T12:00:00+02:00"),
                patch.object(apply, "apply_acceptance", return_value=["milestones.md"]) as call,
            ):
                self.assertEqual(apply.main(), 0)

            kwargs = call.call_args.kwargs
            self.assertEqual(kwargs["source_sha"], "a" * 40)
            self.assertEqual(kwargs["server_source"]["artifact_id"], "42")
            self.assertEqual(kwargs["server_source"]["artifact_digest"], "b" * 64)

    def test_main_rejects_default_branch_and_missing_semantic_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch("sys.argv", self._arguments(root)),
                patch.object(apply, "require_supported_python"),
                patch.object(apply, "find_project_root", return_value=root),
                patch.object(apply, "_git_branch", return_value="main"),
            ):
                with self.assertRaisesRegex(SystemExit, "default branch"):
                    apply.main()

            with (
                patch("sys.argv", self._arguments(root, semantic=False)),
                patch.object(apply, "require_supported_python"),
                patch.object(apply, "find_project_root", return_value=root),
                patch.object(apply, "_git_branch", return_value="feature"),
                patch.object(
                    apply,
                    "validate_evidence_bundle",
                    return_value={
                        "git_sha": "a" * 40,
                        "server_source": {
                            "repository": "example/repo",
                            "workflow": "Project check",
                            "run_id": "1",
                            "run_url": "https://github.com/example/repo/actions/runs/1",
                            "event_sha": "a" * 40,
                        },
                    },
                ),
            ):
                with self.assertRaisesRegex(SystemExit, "--semantic-review"):
                    apply.main()


class ReviewerIndependenceTests(unittest.TestCase):
    """Заявленная независимость смысловой проверки сверяется с авторством.

    `review_context: fresh-session` подтверждается только тем, что кто-то это
    написал. Проверка связывает декларацию с наблюдаемым фактом: проверяющий не
    входит в число авторов проверяемого диапазона. Для проекта одного владельца
    предусмотрен явный режим — он фиксирует отсутствие независимости, а не
    выдаёт совпадение за независимость.
    """

    def _repo(self, tmp: str, author_email: str) -> Path:
        root = Path(tmp)
        # Авторство задаётся через окружение, а не только через git config:
        # внутри `git commit` (например, в pre-commit hook) git экспортирует
        # GIT_AUTHOR_*/GIT_COMMITTER_*, и они перебивают локальный конфиг —
        # коммит во временном репозитории получил бы внешнего автора, и тест
        # проходил бы или падал в зависимости от способа запуска.
        env = dict(os.environ)
        env.update(
            {
                "GIT_AUTHOR_NAME": "Author",
                "GIT_AUTHOR_EMAIL": author_email,
                "GIT_COMMITTER_NAME": "Author",
                "GIT_COMMITTER_EMAIL": author_email,
            }
        )

        def run(*args: str) -> None:
            subprocess.run(args, cwd=root, check=True, capture_output=True, env=env)

        run("git", "init", "-q")
        run("git", "config", "user.email", author_email)
        run("git", "config", "user.name", "Author")
        (root / "f.txt").write_text("x", encoding="utf-8")
        run("git", "add", "-A")
        run("git", "commit", "-qm", "c")
        return root

    def test_reviewer_who_authored_the_range_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo(tmp, "author@example.com")
            with self.assertRaises(ValueError) as raised:
                apply.validate_reviewer_independence(
                    root, {"reviewer": "author@example.com"}, "HEAD"
                )
            self.assertIn("reviewer_is_author_acknowledged", str(raised.exception))

    def test_acknowledged_single_owner_mode_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo(tmp, "author@example.com")
            apply.validate_reviewer_independence(
                root,
                {"reviewer": "author@example.com", "reviewer_is_author_acknowledged": True},
                "HEAD",
            )

    def test_independent_reviewer_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo(tmp, "author@example.com")
            apply.validate_reviewer_independence(root, {"reviewer": "someone@example.com"}, "HEAD")

    def test_reviewer_name_also_counts_not_only_email(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo(tmp, "author@example.com")
            with self.assertRaises(ValueError):
                apply.validate_reviewer_independence(root, {"reviewer": "Author"}, "HEAD")

    def test_missing_reviewer_is_left_to_the_field_check(self) -> None:
        # Пустой reviewer отклоняется отдельной проверкой формы записи;
        # здесь он не должен приводить к ложному совпадению с автором.
        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo(tmp, "author@example.com")
            apply.validate_reviewer_independence(root, {}, "HEAD")


if __name__ == "__main__":
    unittest.main()
