from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import (
    find_project_root,
    git_info,
    read_text,
    require_supported_python,
)
from operations.scripts.evidence.record import build_evidence_bundle, write_evidence_bundle
from operations.scripts.status.generate_project_status import parse_unit_test_summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate evidence bundle from check and test results"
    )
    parser.add_argument("--check-summary", required=True, help="Path to check_summary.json")
    parser.add_argument("--test-returncode", type=int, required=True, help="Unit test return code")
    parser.add_argument("--test-output", default="", help="Unit test output")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--event-sha", required=True)
    args = parser.parse_args()

    require_supported_python()
    root = find_project_root(Path.cwd())

    summary_path = Path(args.check_summary)
    if not summary_path.is_absolute():
        summary_path = root / summary_path

    if not summary_path.exists():
        print(f"ERROR: Check summary not found: {summary_path}")
        return 1

    summary = json.loads(read_text(summary_path))
    current_git = git_info(root)

    bundle = build_evidence_bundle(
        root,
        check_summary=summary,
        test_returncode=args.test_returncode,
        test_output=args.test_output,
        git=current_git,
        server_source={
            "repository": args.repository,
            "workflow": args.workflow,
            "run_id": args.run_id,
            "run_url": args.run_url,
            "event_sha": args.event_sha,
        },
    )
    evidence_path = write_evidence_bundle(root, bundle)

    checks = [item for item in summary.get("checks", []) if isinstance(item, dict)]
    print(f"Checks: {sum(1 for item in checks if item.get('ok'))}/{len(checks)} PASS")
    unit = parse_unit_test_summary(args.test_returncode, args.test_output)
    print(f"Unit tests: {unit['label']}")
    for item in checks:
        for error in item.get("errors", []) if isinstance(item.get("errors"), list) else []:
            print(f"  ERROR {item.get('name')}: {error}")
    if args.test_returncode != 0 and args.test_output:
        print("\n".join(args.test_output.splitlines()[-40:]))
    print(f"Evidence bundle: {evidence_path.relative_to(root).as_posix()}")
    print(f"Acceptance state: {bundle.get('acceptance_state', 'unknown')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
