"""Canonical unittest discovery that fails on every skipped test."""

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import find_project_root


def run_tests(root: Path, *, start_dir: str = "operations/tests", verbosity: int = 1) -> int:
    discovery_root = (root / start_dir).resolve()
    loader = unittest.TestLoader()
    suite = loader.discover(
        str(discovery_root),
        pattern="test_*.py",
        top_level_dir=str(discovery_root),
    )
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    if result.skipped:
        print("\nSkipped tests are forbidden:", file=sys.stderr)
        for test, reason in result.skipped:
            print(f"- {test}: {reason}", file=sys.stderr)
        return 2
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
