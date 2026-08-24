"""
Durability tests for the atomic_write persistence primitive.

Every generator in this repository (documents, tasks, status, evidence)
funnels its writes through atomic_write's temp-file + os.replace pattern.
These tests verify the durability guarantee that pattern is meant to
provide: a failure mid-write must never corrupt or truncate the
previously-committed file, and a successful write must survive being
re-read from disk exactly as written.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import atomic_write, read_text


class CrashDuringWriteTest(unittest.TestCase):
    """Simulate a process crash partway through a write and verify the
    previously-committed file is untouched."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_exception_during_temp_file_write_leaves_original_intact(self) -> None:
        target = self.root / "data.txt"
        atomic_write(target, "original committed content")

        class _BoomOnWrite:
            def __init__(self, real_handle: object) -> None:
                self._real = real_handle

            def write(self, _data: str) -> int:
                raise OSError("simulated disk failure mid-write")

            def __enter__(self) -> "_BoomOnWrite":
                return self

            def __exit__(self, *_exc: object) -> None:
                # A real NamedTemporaryFile's own __exit__ always closes the
                # underlying OS handle even when the body raised - without
                # this, atomic_write's later os.unlink() would fail with
                # PermissionError on Windows, where a file cannot be deleted
                # while still open.
                self._real.__exit__(*_exc)  # type: ignore[attr-defined]
                return None

            @property
            def name(self) -> str:
                return self._real.name  # type: ignore[attr-defined]

        import tempfile as tempfile_module
        from typing import Any

        real_named_temp_file = tempfile_module.NamedTemporaryFile

        def failing_named_temp_file(*args: Any, **kwargs: Any) -> _BoomOnWrite:
            handle = real_named_temp_file(*args, **kwargs)
            return _BoomOnWrite(handle)

        with mock.patch("tempfile.NamedTemporaryFile", side_effect=failing_named_temp_file):
            with self.assertRaises(OSError):
                atomic_write(target, "new content that should never land")

        # The original file must be completely unaffected: no truncation,
        # no partial overwrite, no corruption.
        self.assertEqual(read_text(target), "original committed content\n")

        # No stray temp file should be left in the target directory.
        leftover_temp_files = [path for path in self.root.iterdir() if path.name != "data.txt"]
        self.assertEqual(
            leftover_temp_files,
            [],
            f"Failed write left stray temp file(s): {leftover_temp_files}",
        )

    def test_os_replace_failure_leaves_original_and_no_visible_partial_file(self) -> None:
        target = self.root / "data.txt"
        atomic_write(target, "stable content")

        with mock.patch("os.replace", side_effect=OSError("simulated rename failure")):
            with self.assertRaises(OSError):
                atomic_write(target, "content that must not become visible")

        # Original committed content must survive the failed rename.
        self.assertEqual(read_text(target), "stable content\n")


class ReplaceRetryTest(unittest.TestCase):
    """os.replace() has no POSIX-style guarantee on Windows that a rename
    succeeds while the destination is momentarily open elsewhere; these
    exercise _replace_with_retry's bounded-retry behavior directly rather
    than relying on a genuine Windows-only race to trigger it."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_succeeds_after_transient_permission_errors(self) -> None:
        target = self.root / "data.txt"
        real_replace = os.replace
        calls: list[int] = []

        def flaky_replace(src: str, dst: str) -> None:
            calls.append(1)
            if len(calls) < 3:
                raise PermissionError("transient lock, simulating Windows contention")
            real_replace(src, dst)

        with (
            mock.patch("os.replace", side_effect=flaky_replace),
            mock.patch("time.sleep") as sleep_mock,
        ):
            changed = atomic_write(target, "eventually written")

        self.assertTrue(changed)
        self.assertEqual(read_text(target), "eventually written\n")
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleep_mock.call_count, 2)

    def test_gives_up_after_exhausting_retry_attempts(self) -> None:
        target = self.root / "data.txt"
        atomic_write(target, "original content")
        calls: list[int] = []

        def always_locked(_src: str, _dst: str) -> None:
            calls.append(1)
            raise PermissionError("destination permanently locked")

        with (
            mock.patch("os.replace", side_effect=always_locked),
            mock.patch("time.sleep"),
        ):
            with self.assertRaises(PermissionError):
                atomic_write(target, "content that must not land")

        # Every configured attempt was made, not just one.
        self.assertEqual(len(calls), 5)
        # The original file survives, and the temp file was cleaned up.
        self.assertEqual(read_text(target), "original content\n")
        leftover_temp_files = [path for path in self.root.iterdir() if path.name != "data.txt"]
        self.assertEqual(leftover_temp_files, [])

    def test_non_permission_os_error_is_not_retried(self) -> None:
        target = self.root / "data.txt"
        atomic_write(target, "original content")
        calls: list[int] = []

        def unrelated_failure(_src: str, _dst: str) -> None:
            calls.append(1)
            raise OSError("disk full, unrelated to Windows file locking")

        with mock.patch("os.replace", side_effect=unrelated_failure):
            with self.assertRaises(OSError):
                atomic_write(target, "content that must not land")

        self.assertEqual(len(calls), 1, "Non-PermissionError failures must not be retried")


class ContentIntegrityTest(unittest.TestCase):
    """A successful write must be byte-for-byte recoverable on read."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_round_trip_preserves_unicode_content(self) -> None:
        target = self.root / "unicode.txt"
        content = "Заголовок 🎉 café naïve ́combining"
        atomic_write(target, content)
        self.assertEqual(read_text(target), content + "\n")

    def test_round_trip_preserves_large_content(self) -> None:
        target = self.root / "large.txt"
        content = "line content here\n" * 100_000
        atomic_write(target, content)
        result = read_text(target)
        self.assertEqual(len(result), len(content))
        self.assertEqual(result, content)

    def test_repeated_identical_writes_are_idempotent_no_op(self) -> None:
        target = self.root / "stable.txt"
        first_change = atomic_write(target, "same content")
        second_change = atomic_write(target, "same content")

        self.assertTrue(first_change)
        self.assertFalse(second_change, "Re-writing identical content should report no change")

    def test_line_ending_normalization_is_durable_across_rewrites(self) -> None:
        target = self.root / "mixed_endings.txt"
        atomic_write(target, "line1\r\nline2\rline3\n")
        first_read = read_text(target)

        # Writing the already-normalized content back must be a true no-op.
        changed = atomic_write(target, first_read.rstrip("\n"))
        self.assertFalse(changed)
        self.assertNotIn("\r", read_text(target))

    def test_parent_directories_are_created_durably(self) -> None:
        target = self.root / "deep" / "nested" / "path" / "file.txt"
        self.assertFalse(target.parent.exists())
        atomic_write(target, "content")
        self.assertTrue(target.is_file())
        self.assertEqual(read_text(target), "content\n")


if __name__ == "__main__":
    unittest.main()
