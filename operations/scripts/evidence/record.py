from __future__ import annotations

import json
import re
from pathlib import Path
from typing import cast

from operations.scripts.common.project import atomic_write
from operations.scripts.quality.registry import (
    load_quality_registry,
    profiles_for_milestone,
    validate_server_source,
)
from operations.scripts.status.generate_project_status import (
    ProgressSnapshot,
    build_progress_snapshot,
)


def _evidence_targets(root: Path, snapshot: ProgressSnapshot) -> dict[str, list[str]]:
    acceptance = snapshot["acceptance"]
    milestone_id = snapshot["current"]["id"]
    coverage = acceptance["coverage"]
    milestone_scope = coverage["scope"]
    tracked_targets = coverage["tracked_targets"]
    result: dict[str, list[str]] = {}

    for test in acceptance["tests"]:
        evidence_id = test["automated_evidence"]
        if not evidence_id:
            continue
        targets = result.setdefault(evidence_id, [])
        for value in test["verifies"]:
            if value and value not in targets:
                targets.append(value)
        for value in test["accepts"]:
            item = f"milestone:{value.lower()}"
            if item != "milestone:" and item not in targets:
                targets.append(item)

    # `profile` comes from profiles_for_milestone() in registry.py, which is not yet
    # typed beyond dict[str, object].
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
    context = acceptance["evidence_context"]
    git_sha = str(context.get("git_sha", git.get("commit", "unknown")))
    provenance_errors = validate_server_source(server_source, expected_sha=git_sha)
    if provenance_errors:
        raise ValueError("Некорректный server_source: " + "; ".join(provenance_errors))
    targets_by_evidence = _evidence_targets(root, snapshot)
    # `quality` comes from evaluate_milestone_quality() in registry.py, which is not
    # yet typed beyond dict[str, object]; "evidence"/"profiles" are documented lists.
    quality_evidence = cast(list[dict[str, object]], acceptance["quality"].get("evidence", []))
    quality_profiles = cast(list[object], acceptance["quality"].get("profiles", []))
    evidence_rows = []
    for raw in quality_evidence:
        evidence_id = str(raw.get("id", ""))
        evidence_rows.append({**raw, "targets": targets_by_evidence.get(evidence_id, [])})

    return {
        "schema_version": 2,
        "milestone": snapshot["current"]["id"],
        "acceptance_state": acceptance["state"],
        "blockers": acceptance["blockers"],
        "pending_gates": acceptance["pending_gates"],
        "git_sha": git_sha,
        "timestamp": str(context.get("timestamp", "unknown")),
        "environment": context.get("environment", {}),
        "server_source": server_source,
        "quality_profiles": list(quality_profiles),
        "impacted_profiles": acceptance["impacted_profiles"],
        "coverage_base": acceptance["coverage_base"],
        "changed_paths": acceptance["changed_paths"],
        "uncovered_paths": acceptance["uncovered_paths"],
        "coverage": acceptance["coverage"],
        "evidence": evidence_rows,
        "tests": [
            {
                "test_id": item["id"],
                "result": item["effective_result"],
                "verifies": item["verifies"],
                "accepts": item["accepts"],
                "traces_to": item["traces_to"],
                "automated_evidence": item["automated_evidence"],
            }
            for item in acceptance["tests"]
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
