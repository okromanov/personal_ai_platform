#!/usr/bin/env python3
"""
Auto-increment file version when content changes.

Triggered by pre-commit hook when file metadata (updated field) changes.
Increments version: 1.0 → 1.1 → 1.2 → 2.0 → 2.1, etc.

Usage: python3 operations/scripts/versioning/increment_file_version.py <file_path>
"""

import sys
import re
from pathlib import Path

def increment_version(version_str: str) -> str:
    """Increment semantic version: 1.0 → 1.1, 1.9 → 2.0"""
    match = re.match(r'(\d+)\.(\d+)', version_str)
    if not match:
        return version_str

    major, minor = int(match.group(1)), int(match.group(2))

    if minor < 9:
        return f"{major}.{minor + 1}"
    else:
        return f"{major + 1}.0"

def update_file_version(file_path: str) -> bool:
    """Update version in YAML frontmatter."""
    path = Path(file_path)

    if not path.exists() or not path.suffix == '.md':
        return False

    content = path.read_text(encoding='utf-8')

    # Find version field in frontmatter
    version_match = re.search(r'^version:\s*([0-9.]+)', content, re.MULTILINE)
    if not version_match:
        return False

    old_version = version_match.group(1)
    new_version = increment_version(old_version)

    if old_version != new_version:
        new_content = re.sub(
            r'^version:\s*[0-9.]+',
            f'version: {new_version}',
            content,
            count=1,
            flags=re.MULTILINE
        )
        path.write_text(new_content, encoding='utf-8')
        print(f"  {path}: {old_version} → {new_version}")
        return True

    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 operations/scripts/versioning/increment_file_version.py <file_path> [file_path2 ...]")
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
