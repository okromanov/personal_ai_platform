#!/usr/bin/env python3
"""
Initialize milestone folder and files on transition.

When milestone state changes (planned → in-progress), creates:
- work/m0X/final_report.md, rendered by render_final_report() (the same
  function operations/scripts/milestones/update_completion_report.py uses to
  regenerate it after acceptance) so the initial and final report are always
  the same format, never two hand-kept templates drifting apart.

owner_checklist.md and semantic_review.md are deliberately not generated:
the acceptance checklist and the semantic-review procedure are already
fully specified in operations/acceptance.md and operations/semantic_review.md
respectively, and a per-milestone stub that just restates them (as m01's
owner_checklist.md and m02's semantic_review.md did, before they were
removed) never accumulates milestone-specific content worth keeping. A
milestone that genuinely needs a written record beyond the canonical
procedure (as m01/semantic_review.md does, once a real review happened)
gets one created deliberately, not auto-generated as an empty shell.

Usage: python3 operations/scripts/milestones/init_milestone.py m02
"""

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.milestones.update_completion_report import render_final_report


def _write_if_absent(path: Path, content: str) -> None:
    """Write content only if the file does not already exist.

    Milestone init must stay idempotent: re-running it must never overwrite
    a final report that already carries decisions.
    """
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def init_milestone(milestone_id: str, root: Path | None = None) -> bool:
    """Initialize milestone folder structure."""
    if root is None:
        root = Path.cwd()

    try:
        milestone_dir = root / "work" / milestone_id
        milestone_dir.mkdir(parents=True, exist_ok=True)

        # The initial (pending) final_report.md is rendered by the same
        # function that regenerates it after acceptance, so the two never
        # drift into two different report formats.
        _write_if_absent(milestone_dir / "final_report.md", render_final_report(root, milestone_id))

        return True
    except Exception as e:
        print(f"ERROR: Failed to initialize milestone {milestone_id}: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 operations/scripts/milestones/init_milestone.py <milestone_id>")
        sys.exit(1)

    milestone_id = sys.argv[1]
    if init_milestone(milestone_id):
        print(f"✓ Initialized {milestone_id} folder structure")
        sys.exit(0)
    else:
        print(f"✗ Failed to initialize {milestone_id}")
        sys.exit(1)
