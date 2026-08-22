from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import atomic_write, find_project_root
from operations.scripts.quality.registry import validate_server_source

SHA_PATTERN = re.compile(r"[0-9a-f]{40}")


def build_record(
    root: Path,
    git_sha: str,
    artifacts: list[str],
    *,
    server_source: dict[str, object],
) -> dict[str, object]:
    normalized_sha = git_sha.strip().lower()
    if not SHA_PATTERN.fullmatch(normalized_sha):
        raise ValueError("git_sha должен быть 40-символьным SHA")

    checked: list[dict[str, object]] = []
    for value in artifacts:
        candidate = (root / value).resolve()
        try:
            relative = candidate.relative_to(root.resolve())
        except ValueError as exc:
            raise ValueError(f"Артефакт вне репозитория: {value}") from exc
        if not candidate.is_file() or candidate.stat().st_size == 0:
            raise ValueError(f"Артефакт отсутствует или пуст: {value}")
        checked.append(
            {
                "path": relative.as_posix(),
                "bytes": candidate.stat().st_size,
                "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
            }
        )

    provenance_errors = validate_server_source(server_source, expected_sha=normalized_sha)
    if provenance_errors:
        raise ValueError("Некорректный server_source: " + "; ".join(provenance_errors))

    return {
        "type": "quality_suite",
        "result": "passed",
        "git_sha": normalized_sha,
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "environment": {"runner": "github-actions", "os": "linux"},
        "command": ["python3", "operations/scripts/quality/run_suite.py", "full"],
        "exit_code": 0,
        "artifacts": checked,
        "server_source": server_source,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a completed CI quality suite")
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--artifact", action="append", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--event-sha", required=True)
    args = parser.parse_args()

    root = find_project_root(Path.cwd())
    try:
        record = build_record(
            root,
            args.git_sha,
            list(args.artifact),
            server_source={
                "repository": args.repository,
                "workflow": args.workflow,
                "run_id": args.run_id,
                "run_url": args.run_url,
                "event_sha": args.event_sha,
            },
        )
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    try:
        output.resolve().relative_to(root.resolve())
    except ValueError:
        print("ERROR: output должен находиться внутри репозитория")
        return 1
    atomic_write(output, json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(f"Quality evidence: {output.relative_to(root).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
