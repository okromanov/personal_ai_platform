"""Canonical unittest discovery that fails on every skipped test."""

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import find_project_root

# Skips are forbidden as a rule -- an unexplained skip hides a test that
# should either run or be deleted. The one standing exception is a test
# whose *implementation*, not its assertion, is platform-bound (here: a
# helper written in Bash, which Windows CI has no shell for); that is a
# permanent, documented fact about the environment, not something to
# "eventually fix" the way an ordinary skip is.
_ALLOWED_SKIP_REASONS = frozenset({"the canonical helper is a Bash script"})


def run_tests(root: Path, *, start_dir: str = "operations/tests", verbosity: int = 1) -> int:
    discovery_root = (root / start_dir).resolve()
    loader = unittest.TestLoader()
    suite = loader.discover(
        str(discovery_root),
        pattern="test_*.py",
        top_level_dir=str(discovery_root),
    )
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    unexplained_skips = [
        (test, reason) for test, reason in result.skipped if reason not in _ALLOWED_SKIP_REASONS
    ]
    if unexplained_skips:
        print("\nSkipped tests are forbidden:", file=sys.stderr)
        for test, reason in unexplained_skips:
            print(f"- {test}: {reason}", file=sys.stderr)
        return 2
    if result.unexpectedSuccesses:
        # wasSuccessful() already treats this as a failure, but folded into
        # a generic exit 1 it's indistinguishable from an assertion failure
        # -- an @expectedFailure test that started passing needs its
        # decorator removed, not a debugging session over a stack trace
        # that doesn't exist.
        print("\nExpectedFailure tests unexpectedly passed:", file=sys.stderr)
        for test in result.unexpectedSuccesses:
            print(f"- {test}", file=sys.stderr)
        return 3
    return 0 if result.wasSuccessful() else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run repository unit tests and reject skips")
    parser.add_argument("--start-dir", default="operations/tests")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    root = find_project_root(Path.cwd())
    return run_tests(root, start_dir=args.start_dir, verbosity=2 if args.verbose else 1)


if __name__ == "__main__":
    raise SystemExit(main())
