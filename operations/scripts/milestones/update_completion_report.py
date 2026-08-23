#!/usr/bin/env python3
"""
Update milestone final_report.md when milestone is completed.

Synchronizes completion_state and content of final_report.md with actual milestone status.
Called when milestone transitions from in-progress/planned to completed.

Usage: python3 operations/scripts/milestones/update_completion_report.py m01
"""

import re
import sys
from datetime import date
from pathlib import Path


def update_completion_report(milestone_id: str, root: Path | None = None) -> bool:
    """Update final_report.md for completed milestone."""
    if root is None:
        root = Path.cwd()

    try:
        report_path = root / "work" / milestone_id / "final_report.md"
        if not report_path.exists():
            return False

        content = report_path.read_text(encoding="utf-8")
        today = date.today().isoformat()

        # Update completion_state in frontmatter
        if "completion_state: pending" in content:
            content = content.replace("completion_state: pending", "completion_state: completed")

        # Update content section 1: Состояние завершения
        content = re.sub(
            r"^- Статус: в процессе$",
            "- Статус: завершено",
            content,
            flags=re.MULTILINE,
        )

        content = re.sub(
            r"^- Дата завершения: —$",
            f"- Дата завершения: {today}",
            content,
            flags=re.MULTILINE,
        )

        content = re.sub(
            r"^- Все задачи завершены: нет$",
            "- Все задачи завершены: да",
            content,
            flags=re.MULTILINE,
        )

        # Update version and date
        content = re.sub(
            r"^updated: \d{4}-\d{2}-\d{2}$",
            f"updated: {today}",
            content,
            flags=re.MULTILINE,
        )

        report_path.write_text(content, encoding="utf-8")
        return True

    except Exception as e:
        print(f"ERROR: Failed to update {milestone_id} final_report: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python3 operations/scripts/milestones/update_completion_report.py <milestone_id>"
        )
        sys.exit(1)

    milestone_id = sys.argv[1]
    if update_completion_report(milestone_id):
        print(f"✓ Updated {milestone_id} final_report.md")
        sys.exit(0)
    else:
        print(f"✗ Failed to update {milestone_id}")
        sys.exit(1)
