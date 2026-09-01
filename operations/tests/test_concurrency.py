"""
Concurrency safety tests.

The codebase itself has no threading or asyncio in operations/scripts — but
multiple developers or CI runners can invoke the quality tooling concurrently
against the same working tree (e.g. two `pre-commit` hooks racing on the same
generated file, or a local run overlapping with a CI checkout). The one
shared-mutable-state primitive that matters here is `atomic_write`, which
every generator (documents, tasks, status) funnels through. These tests
verify it never leaves a file half-written or corrupted under concurrent
callers, using real OS threads so the interleaving is genuine, not simulated.
"""

from __future__ import annotations

import sys
import tempfile
import threading
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import atomic_write, read_text


class AtomicWriteConcurrencyTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_concurrent_writers_never_produce_torn_content(self) -> None:
        """Many threads racing to write distinct full payloads to the same
        path must always leave one complete payload, never a mix of two."""
        target = self.root / "shared.txt"
        payload_size = 50_000
        thread_count = 16
        payloads = [
            f"writer-{i}:" + ("A" if i % 2 == 0 else "B") * payload_size
            for i in range(thread_count)
        ]

        errors: list[BaseException] = []
        barrier = threading.Barrier(thread_count)

        def writer(payload: str) -> None:
            try:
                barrier.wait(timeout=5)
                atomic_write(target, payload)
            except BaseException as exc:  # noqa: BLE001 - surfaced via errors list
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(p,)) for p in payloads]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertEqual(errors, [], f"Writer threads raised: {errors}")

        final_content = read_text(target).rstrip("\n")
        matching_payloads = [p for p in payloads if p == final_content]
        self.assertEqual(
            len(matching_payloads),
            1,
            "Final file content must exactly equal exactly one writer's payload "
            "(no torn/interleaved write), got a mismatch instead",
        )

    def test_readers_never_observe_partial_write_during_concurrent_update(self) -> None:
        """A reader running concurrently with writers must always see a
        complete, previously-written value — never a truncated fragment."""
        target = self.root / "read_during_write.txt"
        stable_values = [f"value-{i}" * 10_000 for i in range(8)]
        atomic_write(target, stable_values[0])

        stop = threading.Event()
        observed_invalid: list[str] = []

        def reader() -> None:
            while not stop.is_set():
                try:
                    content = read_text(target).rstrip("\n")
                except FileNotFoundError:
                    continue
                if content not in stable_values:
                    observed_invalid.append(content)

        def writer() -> None:
            for value in stable_values[1:]:
                atomic_write(target, value)

        reader_thread = threading.Thread(target=reader)
        writer_thread = threading.Thread(target=writer)
        reader_thread.start()
        writer_thread.start()
        writer_thread.join(timeout=10)
        stop.set()
        reader_thread.join(timeout=10)

        self.assertEqual(
            observed_invalid,
            [],
            f"Reader observed {len(observed_invalid)} torn/invalid values during concurrent write",
        )

    def test_concurrent_writes_to_distinct_files_all_succeed(self) -> None:
        """Sanity check: independent files under concurrent load don't
        interfere with each other (no shared temp-name collisions)."""
        thread_count = 32
        errors: list[BaseException] = []

        def writer(index: int) -> None:
            try:
                atomic_write(self.root / f"file_{index}.txt", f"content-{index}")
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(thread_count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertEqual(errors, [])
        for index in range(thread_count):
            self.assertEqual(
                read_text(self.root / f"file_{index}.txt").rstrip("\n"), f"content-{index}"
            )


if __name__ == "__main__":
    unittest.main()
