#!/usr/bin/env python3
"""
Auto-increment file version when content changes.

Triggered by pre-commit hook when file metadata (updated field) changes.
Increments the minor version only: 1.0 → 1.1 → … → 1.9 → 1.10. A new major
version is an explicit owner decision (operations/change_process.md §3),
so this hook never creates one.

Usage: python3.12 operations/scripts/versioning/increment_file_version.py <file_path>
"""

import io
import re
import sys
from pathlib import Path
from typing import cast


def _configure_utf8_stdout() -> None:
    try:
        cast("io.TextIOWrapper", sys.stdout).reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def increment_version(version_str: str) -> str:
    """Increment the minor version: 1.0 → 1.1, 1.9 → 1.10."""
    match = re.match(r"(\d+)\.(\d+)", version_str)
    if not match:
        return version_str

    major, minor = int(match.group(1)), int(match.group(2))

    return f"{major}.{minor + 1}"


def update_file_version(file_path: str) -> bool:
    """Update version in YAML frontmatter."""
    try:
        path = Path(file_path)

        if not path.exists() or not path.suffix == ".md":
            return False

        content = path.read_text(encoding="utf-8")

        # Fully auto-generated files own their `version` field via their generator
        # (which always writes a fixed value); bumping it here would only be undone
        # by the next generate.py run, producing permanent drift between the two.
        if content.startswith("<!-- generated file: do not edit manually -->"):
            return False
        if re.search(r"(?m)^type:\s*milestone_completion_report\s*$", content):
            return False

        # Find version field in frontmatter
        version_match = re.search(r"^version:\s*([0-9.]+)", content, re.MULTILINE)
        if not version_match:
            return False

        old_version = version_match.group(1)
        new_version = increment_version(old_version)

        if old_version != new_version:
            new_content = re.sub(
                r"^version:\s*[0-9.]+",
                f"version: {new_version}",
                content,
                count=1,
                flags=re.MULTILINE,
            )
            path.write_text(new_content, encoding="utf-8")
            print(f"  {path}: {old_version} → {new_version}")
            return True

        return False
    except Exception as e:
        print(
            f"WARNING: Failed to update version in {file_path}: {e}",
            file=sys.stderr,
        )
        return False


if __name__ == "__main__":
    _configure_utf8_stdout()
    if len(sys.argv) < 2:
        print(
            "Usage: python3 "
            "operations/scripts/versioning/increment_file_version.py "
            "<file_path> [file_path2 ...]"
        )
        sys.exit(1)

    updated_count = 0
    for file_path in sys.argv[1:]:
        if update_file_version(file_path):
            updated_count += 1

    if updated_count > 0:
        print(f"✓ Updated {updated_count} file version(s)")
        sys.exit(0)
    else:
        sys.exit(0)
