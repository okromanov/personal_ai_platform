from __future__ import annotations

import json
import re
from pathlib import Path

from operations.scripts.common.project import atomic_write
from operations.scripts.quality.registry import (
    load_quality_registry,
    profiles_for_milestone,
    validate_server_source,
)
from operations.scripts.status.generate_project_status import build_progress_snapshot


def _evidence_targets(root: Path, snapshot: dict[str, object]) -> dict[str, list[str]]:
    acceptance = snapshot["acceptance"]
    milestone_id = str(snapshot["current"]["id"])
    coverage = acceptance.get("coverage", {})
    milestone_scope = [str(value) for value in coverage.get("scope", [])]
    tracked_targets = [str(value) for value in coverage.get("tracked_targets", [])]
    result: dict[str, list[str]] = {}

    for test in acceptance.get("tests", []):
        if not isinstance(test, dict):
            continue
        evidence_id = str(test.get("automated_evidence", ""))
        if not evidence_id:
            continue
        targets = result.setdefault(evidence_id, [])
        for value in test.get("verifies", []):
            item = str(value)
            if item and item not in targets:
                targets.append(item)
        for value in test.get("accepts", []):
            item = f"milestone:{str(value).lower()}"
            if item != "milestone:" and item not in targets:
                targets.append(item)

    registry = load_quality_registry(root)
    for _, profile in profiles_for_milestone(registry, milestone_id):
        profile_targets = list(tracked_targets or milestone_scope)
        if not profile_targets:
            profile_targets = [f"path:{value}" for value in profile.get("paths", []) if str(value)]
        if str(profile.get("scope_coverage", "task_test")) == "global_evidence":
            for evidence_id in profile.get("scope_evidence", []):
                result[str(evidence_id)] = list(profile_targets)
        for evidence_id in profile.get("required_evidence", []):
            result.setdefault(str(evidence_id), list(profile_targets))
    return result


def build_evidence_bundle(
    root: Path,
    *,
    check_summary: dict[str, object],
    test_returncode: int,
    test_output: str,
    git: dict[str, object],
    server_source: dict[str, object],
) -> dict[str, object]:
    snapshot = build_progress_snapshot(
        root,
        check_summary=check_summary,
        test_returncode=test_returncode,
        test_output=test_output,
        git=git,
    )
    acceptance = snapshot["acceptance"]
    context = acceptance.get("evidence_context", {})
    git_sha = str(context.get("git_sha", git.get("commit", "unknown")))
    provenance_errors = validate_server_source(server_source, expected_sha=git_sha)
    if provenance_errors:
        raise ValueError("Некорректный server_source: " + "; ".join(provenance_errors))
    targets_by_evidence = _evidence_targets(root, snapshot)
    evidence_rows = []
    for raw in acceptance.get("quality", {}).get("evidence", []):
        if not isinstance(raw, dict):
            continue
        evidence_id = str(raw.get("id", ""))
        evidence_rows.append({**raw, "targets": targets_by_evidence.get(evidence_id, [])})

    return {
        "schema_version": 2,
        "milestone": str(snapshot["current"]["id"]),
        "acceptance_state": str(acceptance["state"]),
        "blockers": list(acceptance.get("blockers", [])),
        "pending_gates": list(acceptance.get("pending_gates", [])),
        "git_sha": git_sha,
        "timestamp": str(context.get("timestamp", "unknown")),
        "environment": context.get("environment", {}),
        "server_source": server_source,
        "quality_profiles": list(acceptance.get("quality", {}).get("profiles", [])),
        "impacted_profiles": list(acceptance.get("impacted_profiles", [])),
        "coverage_base": acceptance.get("coverage_base", {}),
        "changed_paths": list(acceptance.get("changed_paths", [])),
        "uncovered_paths": list(acceptance.get("uncovered_paths", [])),
        "coverage": acceptance.get("coverage", {}),
        "evidence": evidence_rows,
        "tests": [
            {
                "test_id": str(item.get("id", "")),
                "result": str(item.get("effective_result", "missing")),
                "verifies": list(item.get("verifies", [])),
                "accepts": list(item.get("accepts", [])),
                "traces_to": list(item.get("traces_to", [])),
                "automated_evidence": str(item.get("automated_evidence", "")),
            }
            for item in acceptance.get("tests", [])
            if isinstance(item, dict)
        ],
    }


def write_evidence_bundle(root: Path, bundle: dict[str, object]) -> Path:
    sha = str(bundle.get("git_sha", "unknown")).strip().lower()
    safe_sha = sha if re.fullmatch(r"[0-9a-f]{40}", sha) else "unknown"
    path = root / "runtime" / "evidence" / f"evidence_{safe_sha}.json"
    atomic_write(path, json.dumps(bundle, ensure_ascii=False, indent=2) + "\n")
    latest = root / "runtime" / "evidence" / "latest.json"
    atomic_write(latest, json.dumps(bundle, ensure_ascii=False, indent=2) + "\n")
    return path
