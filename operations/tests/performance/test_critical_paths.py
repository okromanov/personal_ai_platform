"""
Performance regression tests for critical, frequently-invoked functions.

Uses plain wall-clock timing (time.perf_counter) rather than pytest-benchmark
so these tests run under the project's canonical unittest runner without
introducing a second test framework. Thresholds are generous ceilings meant
to catch algorithmic regressions (e.g. an accidental O(n^2) loop), not to
enforce tight performance SLAs.
"""

from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import atomic_write, read_text
from operations.scripts.documents.check import _path_part_uses_snake_case


def _measure(func, *args, **kwargs) -> float:
    start = time.perf_counter()
    func(*args, **kwargs)
    return time.perf_counter() - start


class AtomicWritePerformanceTest(unittest.TestCase):
    """atomic_write must scale linearly with content size, not quadratically."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_atomic_write_scales_linearly_with_file_count(self) -> None:
        # Warm up interpreter/filesystem caches so the first measured batch
        # isn't skewed by one-time cold-start costs (module import, first
        # directory access, etc.) — the dominant source of flakiness here.
        self._write_n_files(50, prefix="warmup")

        small_count = 500
        large_count = 5000  # 10x the files

        small_duration = self._write_n_files(small_count, prefix="small")
        large_duration = self._write_n_files(large_count, prefix="large")

        # An absolute ceiling catches a real regression regardless of ratio
        # noise on fast, small operations. Generous enough to absorb slow CI
        # I/O (e.g. Windows runners with real-time antivirus scanning on
        # every file create, routinely 2-3x slower than Linux for this).
        self.assertLess(
            large_duration,
            20.0,
            f"atomic_write on {large_count} files took {large_duration:.3f}s — expected well under 20s",
        )
        # Generous ratio check (40x slack for a 10x input) as a secondary
        # signal for genuine super-linear behavior, without being fragile
        # against filesystem noise on the small, fast baseline run.
        self.assertLess(
            large_duration,
            max(small_duration * 40, 4.0),
            f"atomic_write on {large_count} files took {large_duration:.3f}s vs "
            f"{small_duration:.3f}s for {small_count} files — looks super-linear",
        )

    def _write_n_files(self, count: int, *, prefix: str = "file") -> float:
        start = time.perf_counter()
        for index in range(count):
            atomic_write(self.root / f"{prefix}_{index}.txt", f"content-{index}")
        return time.perf_counter() - start

    def test_atomic_write_no_op_is_fast(self) -> None:
        """Re-writing identical content should short-circuit via the read+compare path."""
        path = self.root / "stable.txt"
        atomic_write(path, "stable content")

        duration = _measure(atomic_write, path, "stable content")
        self.assertLess(duration, 0.05, "No-op atomic_write should be near-instant")


class DocumentCheckPerformanceTest(unittest.TestCase):
    """Path validation must not degrade badly on deep/large trees."""

    def test_snake_case_check_handles_many_calls_quickly(self) -> None:
        sample_parts = [f"module_{i}_name" for i in range(10_000)]

        duration = _measure(lambda: [_path_part_uses_snake_case(part) for part in sample_parts])
        self.assertLess(
            duration,
            1.0,
            f"10,000 snake_case checks took {duration:.3f}s — expected sub-second",
        )


class ReadTextPerformanceTest(unittest.TestCase):
    """Reading large files must remain roughly linear in file size."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_read_text_scales_with_size(self) -> None:
        small_path = self.root / "small.txt"
        large_path = self.root / "large.txt"
        small_path.write_text("x" * 10_000, encoding="utf-8")
        large_path.write_text("x" * 1_000_000, encoding="utf-8")  # 100x larger

        small_duration = _measure(read_text, small_path)
        large_duration = _measure(read_text, large_path)

        self.assertLess(
            large_duration,
            max(small_duration * 200, 0.5),
            f"read_text on 100x larger file took {large_duration:.3f}s vs "
            f"{small_duration:.3f}s — looks worse than linear",
        )


if __name__ == "__main__":
    unittest.main()
