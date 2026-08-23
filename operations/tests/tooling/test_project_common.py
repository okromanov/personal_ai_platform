from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from operations.scripts.common.project import git_info, read_text


class GitInfoTests(unittest.TestCase):
    def test_repository_with_no_commits_reports_none_not_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(
                ["git", "init", "-q", "-b", "main"], cwd=root, check=True, capture_output=True
            )
            info = git_info(root)
            self.assertEqual(info["commit"], "none")
            self.assertEqual(info["commit_short"], "none")

    def test_repository_with_a_commit_reports_full_sha(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def git(*args: str) -> None:
                subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)

            git("init", "-q", "-b", "main")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.invalid")
            (root / "a.md").write_text("x\n", encoding="utf-8")
            git("add", "a.md")
            git("commit", "-q", "-m", "initial")

            info = git_info(root)
            self.assertEqual(len(str(info["commit"])), 40)
            self.assertNotEqual(info["commit"], "HEAD")


class ReadTextTests(unittest.TestCase):
    def test_invalid_utf8_raises_with_path_in_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.md"
            path.write_bytes(b"---\nid: TEST_001\n---\n\xff\xfe invalid\n")
            with self.assertRaises(ValueError) as ctx:
                read_text(path)
            self.assertIn(str(path), str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
