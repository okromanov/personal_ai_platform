"""Gate check for a published audit: only a complete audit may be published.

operations/repository_audit_system_prompt.md §3.4 and §11 forbid partial
audits. A dated audit baseline added by a change must therefore come with an
evidence package proving three things against the git history itself, not
against the auditor's word:

1. the audit ran in an attested environment (`environment_attestation.json`
   with `ready: true`) whose recorded tree digest matches the audited commit;
2. the file-role inventory covers every tracked file of that commit
   (full-repository mode) with no `NOT_CHECKED` entry;
3. every register entry that existed at that commit was re-evaluated
   (`previous_findings.json`), none left `NOT_CHECKED`.

Only newly added baselines are checked; published history stays immutable.
"""

from __future__ import annotations

import json
from pathlib import Path

from operations.scripts.audit.prepare_environment import (
    SCHEMA,
    Runner,
    run_command,
    tree_digest,
)
from operations.scripts.quality.run_suite import AUDIT_REGISTER_PATH, AUDIT_ROW

EVIDENCE_DIRECTORY = "work/audit/evidence/{date}_completion"
REQUIRED_EVIDENCE = (
    "manifest.json",
    "environment_attestation.json",
    "file_role_inventory.json",
    "previous_findings.json",
)
FULL_MODES = {"FULL", "FULL_REPOSITORY"}
EVALUATIONS = {"CONFIRMED", "REFUTED", "REGRESSION"}
_SHOWN = 5


def _show(run: Runner, root: Path, revision: str, path: str) -> str | None:
    result = run(["git", "show", f"{revision}:{path}"], root, 60)
    return result.stdout if result.returncode == 0 else None


def _load_json(run: Runner, root: Path, head: str, path: str, errors: list[str]) -> object:
    text = _show(run, root, head, path)
    if text is None:
        errors.append(f"{path}: обязательный файл evidence-пакета отсутствует")
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"{path}: некорректный JSON ({exc.msg})")
        return None


def _listing(items: list[str]) -> str:
    extra = f" и ещё {len(items) - _SHOWN}" if len(items) > _SHOWN else ""
    return ", ".join(items[:_SHOWN]) + extra


def _tracked_paths(run: Runner, root: Path, sha: str) -> set[str] | None:
    result = run(["git", "ls-tree", "-r", "-z", "--name-only", "--full-tree", sha], root, 60)
    if result.returncode != 0:
        return None
    return {path for path in result.stdout.split("\0") if path}


def _check_attestation(
    run: Runner, root: Path, attestation: object, where: str, errors: list[str]
) -> str | None:
    if not isinstance(attestation, dict):
        errors.append(f"{where}: attestation обязан быть JSON-объектом")
        return None
    if attestation.get("schema") != SCHEMA:
        errors.append(f"{where}: неизвестная схема attestation {attestation.get('schema')!r}")
        return None
    sha = str(attestation.get("target_sha", ""))
    checks = attestation.get("checks")
    failed = (
        [
            str(check.get("name"))
            for check in checks
            if isinstance(check, dict) and check.get("passed") is not True
        ]
        if isinstance(checks, list)
        else ["checks"]
    )
    if attestation.get("ready") is not True or failed or not checks:
        errors.append(
            f"{where}: среда аудита не была готова (ready != true; "
            f"невыполненные условия: {_listing(failed) or 'нет данных'})"
        )
    tree = attestation.get("tree")
    try:
        entries, digest = tree_digest(run, root, sha)
    except RuntimeError:
        errors.append(f"{where}: проверенный коммит {sha or '?'} недоступен в истории репозитория")
        return None
    if not isinstance(tree, dict) or tree.get("entries") != entries or tree.get("sha256") != digest:
        errors.append(
            f"{where}: дерево в attestation не совпадает с деревом коммита {sha}; "
            "среда подготовлена не для проверенной ревизии"
        )
    return sha


def _check_inventory(
    inventory: object, tracked: set[str], full: bool, where: str, errors: list[str]
) -> None:
    files = inventory.get("files") if isinstance(inventory, dict) else None
    if not isinstance(files, list):
        errors.append(f"{where}: ожидается объект со списком files")
        return
    covered: set[str] = set()
    not_checked: list[str] = []
    for entry in files:
        if not isinstance(entry, dict):
            continue
        paths = entry.get("paths") or [entry.get("path")]
        names = [str(path) for path in paths if path]
        covered.update(names)
        if entry.get("evidence_state") == "NOT_CHECKED":
            not_checked.extend(names)
    if not_checked:
        errors.append(
            f"{where}: {len(not_checked)} файлов помечены NOT_CHECKED: {_listing(sorted(not_checked))}"
        )
    unknown = sorted(covered - tracked)
    if unknown:
        errors.append(f"{where}: пути вне проверенного коммита: {_listing(unknown)}")
    missing = sorted(tracked - covered) if full else []
    if missing:
        errors.append(
            f"{where}: {len(missing)} tracked-файлов не вошли в инвентарь: {_listing(missing)}"
        )


def _check_previous_findings(
    run: Runner, root: Path, sha: str, findings: object, where: str, errors: list[str]
) -> None:
    records = findings.get("records") if isinstance(findings, dict) else None
    if not isinstance(records, list):
        errors.append(f"{where}: ожидается объект со списком records")
        return
    register = _show(run, root, sha, AUDIT_REGISTER_PATH.as_posix()) or ""
    expected = set()
    for line in register.splitlines():
        match = AUDIT_ROW.match(line)
        if match:
            expected.add(match.group("linked_id") or match.group("bare_id"))
    evaluated: dict[str, str] = {}
    for record in records:
        if isinstance(record, dict):
            evaluated[str(record.get("id"))] = str(record.get("evaluation"))
    missing = sorted(expected - set(evaluated))
    if missing:
        errors.append(f"{where}: не перепроверены записи реестра: {_listing(missing)}")
    unresolved = sorted(
        finding_id for finding_id, value in evaluated.items() if value not in EVALUATIONS
    )
    if unresolved:
        errors.append(
            f"{where}: записи без итоговой оценки CONFIRMED/REFUTED/REGRESSION: "
            f"{_listing(unresolved)}"
        )


def validate_published_audit(
    root: Path, head: str, baseline_path: str, *, run: Runner = run_command
) -> list[str]:
    """Check the evidence package of one newly added dated audit baseline."""
    date = Path(baseline_path).stem.removeprefix("audit_baseline_")
    directory = EVIDENCE_DIRECTORY.format(date=date)
    errors: list[str] = []
    loaded = {
        name: _load_json(run, root, head, f"{directory}/{name}", errors)
        for name in REQUIRED_EVIDENCE
    }
    if any(value is None for value in loaded.values()):
        return [f"{baseline_path}: {error}" for error in errors]
    sha = _check_attestation(
        run,
        root,
        loaded["environment_attestation.json"],
        f"{directory}/environment_attestation.json",
        errors,
    )
    manifest = loaded["manifest.json"]
    mode = str(manifest.get("mode", "")) if isinstance(manifest, dict) else ""
    if sha is not None:
        manifest_sha = manifest.get("head_sha") if isinstance(manifest, dict) else None
        if manifest_sha != sha:
            errors.append(
                f"{directory}/manifest.json: head_sha {manifest_sha!r} не совпадает с "
                f"проверенным в attestation {sha}"
            )
        tracked = _tracked_paths(run, root, sha) or set()
        _check_inventory(
            loaded["file_role_inventory.json"],
            tracked,
            mode.upper() in FULL_MODES,
            f"{directory}/file_role_inventory.json",
            errors,
        )
        _check_previous_findings(
            run,
            root,
            sha,
            loaded["previous_findings.json"],
            f"{directory}/previous_findings.json",
            errors,
        )
    return [f"{baseline_path}: {error}" for error in errors]
