"""Prepare and attest an isolated environment for a repository audit.

operations/repository_audit_system_prompt.md §3.4 makes this the entry point
of every audit: exit code 0 only when every precondition holds; any other
exit code means the audit does not start and no audit result is produced.

The environment reproduces everything the project itself verifies - the
canonical gate and the CI checks: a full clone at the exact SHA, the
hash-pinned development tools, the pinned gitleaks/actionlint/syft binaries
CI uses, a working render browser, shellcheck, a running docker daemon and the
repository hooks. `prepare` creates what can be created and then verifies;
`verify` only re-checks an existing environment, e.g. when an audit continues
in a new session. Both write the same attestation.

Readiness means that every check can run, not that the repository passes it:
a red gate is a finding of the audit, not a reason to refuse the audit.
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import io
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import REQUIRED_PYTHON

SCHEMA = "audit_environment_attestation/1"
DEFAULT_TIMEOUT_SECONDS = 600
INSTALL_TIMEOUT_SECONDS = 1800
DOWNLOAD_TIMEOUT_SECONDS = 120
REQUIREMENTS_PATH = "operations/quality/requirements_dev.txt"
HOOKS = {
    "pre-commit": "operations/hooks/pre_commit_hook.sh",
    "pre-push": "operations/hooks/pre_push_hook.sh",
}
PYTHON_TOOLS = ("ruff", "mypy", "bandit", "vulture", "coverage", "pip_audit")
# Host tools CI takes from its runner image; they cannot be pinned here, only
# required. docker must reach a running daemon: CI builds and runs the image.
HOST_TOOLS: dict[str, tuple[str, ...]] = {
    "shellcheck": ("shellcheck", "--version"),
    "docker": ("docker", "version", "--format", "{{.Server.Version}}"),
}
# The same call the canonical render gate makes, so a passing probe means the
# gate step can run - not merely that some browser exists somewhere.
RENDER_PROBE = (
    "from operations.scripts.documents.diagram_render_lint import measure_svg_elements\n"
    'boxes = measure_svg_elements(\'<svg xmlns="http://www.w3.org/2000/svg" '
    'width="40" height="20"><text x="2" y="14">a</text></svg>\')\n'
    "raise SystemExit(0 if boxes else 1)\n"
)
_MACHINES = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "arm64": "arm64"}


@dataclass(frozen=True)
class PinnedBinary:
    """A release binary CI uses, pinned to the release's published SHA-256."""

    name: str
    version: str
    base_url: str
    version_args: tuple[str, ...]
    assets: dict[tuple[str, str], tuple[str, str]]


# Every SHA-256 comes from the release's own *_checksums.txt. The linux x64
# gitleaks and actionlint values are the ones .github/workflows/project_check.yml
# pins (kept equal by a test); syft is the version anchore/sbom-action pins at
# the commit CI uses (src/SyftVersion.ts).
PINNED_BINARIES = (
    PinnedBinary(
        "gitleaks",
        "8.30.1",
        "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/",
        ("version",),
        {
            ("linux", "x64"): (
                "gitleaks_8.30.1_linux_x64.tar.gz",
                "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
            ),
            ("linux", "arm64"): (
                "gitleaks_8.30.1_linux_arm64.tar.gz",
                "e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080",
            ),
            ("darwin", "x64"): (
                "gitleaks_8.30.1_darwin_x64.tar.gz",
                "dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a18081af1952709",
            ),
            ("darwin", "arm64"): (
                "gitleaks_8.30.1_darwin_arm64.tar.gz",
                "b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5",
            ),
            ("windows", "x64"): (
                "gitleaks_8.30.1_windows_x64.zip",
                "d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e",
            ),
            ("windows", "arm64"): (
                "gitleaks_8.30.1_windows_arm64.zip",
                "b95f5e4f5c425cedca7ee203d9afd29597e692c4924a12ed42f970537c72cc0f",
            ),
        },
    ),
    PinnedBinary(
        "actionlint",
        "1.7.12",
        "https://github.com/rhysd/actionlint/releases/download/v1.7.12/",
        ("-version",),
        {
            ("linux", "x64"): (
                "actionlint_1.7.12_linux_amd64.tar.gz",
                "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8",
            ),
            ("linux", "arm64"): (
                "actionlint_1.7.12_linux_arm64.tar.gz",
                "325e971b6ba9bfa504672e29be93c24981eeb1c07576d730e9f7c8805afff0c6",
            ),
            ("darwin", "x64"): (
                "actionlint_1.7.12_darwin_amd64.tar.gz",
                "5b44c3bc2255115c9b69e30efc0fecdf498fdb63c5d58e17084fd5f16324c644",
            ),
            ("darwin", "arm64"): (
                "actionlint_1.7.12_darwin_arm64.tar.gz",
                "aba9ced2dee8d27fecca3dc7feb1a7f9a52caefa1eb46f3271ea66b6e0e6953f",
            ),
            ("windows", "x64"): (
                "actionlint_1.7.12_windows_amd64.zip",
                "6e7241b51e6817ea6a047693d8e6fed13b31819c9a0dd6c5a726e1592d22f6e9",
            ),
            ("windows", "arm64"): (
                "actionlint_1.7.12_windows_arm64.zip",
                "cadcf7ea4efe3a68728893813643cebe1185e5b1d4be5b96245f65c9a4d5ea41",
            ),
        },
    ),
    PinnedBinary(
        "syft",
        "1.42.3",
        "https://github.com/anchore/syft/releases/download/v1.42.3/",
        ("version",),
        {
            ("linux", "x64"): (
                "syft_1.42.3_linux_amd64.tar.gz",
                "0d6be741479eddd2c8644a288990c04f3df0d609bbc1599a005532a9dff63509",
            ),
            ("linux", "arm64"): (
                "syft_1.42.3_linux_arm64.tar.gz",
                "dc630590c953347789d08f8ebf57c7d8094db89100785fcd94b1cddeac791804",
            ),
            ("darwin", "x64"): (
                "syft_1.42.3_darwin_amd64.tar.gz",
                "c00d01b7c43504708c8922d643d1cbaefa62ca8876baa4d2c2cf4c3be43707a9",
            ),
            ("darwin", "arm64"): (
                "syft_1.42.3_darwin_arm64.tar.gz",
                "d71ee7db2be0fe2e96f679fd9d69ef04274cc86c8604707797080a21070b3f32",
            ),
            ("windows", "x64"): (
                "syft_1.42.3_windows_amd64.zip",
                "e1b9f4945aa64c2b34970bec617623d7f803d0661b48a50b966768b363322e2d",
            ),
            ("windows", "arm64"): (
                "syft_1.42.3_windows_arm64.zip",
                "76db35f9ec13628e8465685e9773e7de4f57efe1f05bb99959fdde59bdef5f6a",
            ),
        },
    ),
)


@dataclass(frozen=True)
class Completed:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


Runner = Callable[[Sequence[str], Path | None, int], Completed]
Downloader = Callable[[str], bytes]


def run_command(
    argv: Sequence[str], cwd: Path | None = None, timeout: int = DEFAULT_TIMEOUT_SECONDS
) -> Completed:
    env = {**os.environ, "PYTHONUTF8": "1"}
    try:
        proc = subprocess.run(
            list(argv),
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        return Completed(127, "", str(exc))
    except subprocess.TimeoutExpired:
        return Completed(124, "", f"timeout after {timeout}s")
    return Completed(proc.returncode, proc.stdout, proc.stderr)


def download(url: str) -> bytes:
    if not url.startswith("https://"):
        raise ValueError(f"refusing non-https download: {url}")
    opener = urllib.request.build_opener()
    with opener.open(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        if not str(response.geturl()).startswith("https://"):
            raise ValueError(f"download redirected away from https: {response.geturl()}")
        return bytes(response.read())


def sanitize_source(source: str) -> str:
    """Drop credentials from a URL so the attestation never records them."""
    parts = urlsplit(source)
    if not parts.scheme or "@" not in parts.netloc:
        return source
    return urlunsplit(parts._replace(netloc=parts.netloc.rsplit("@", 1)[1]))


def platform_key(system: str | None = None, machine: str | None = None) -> tuple[str, str]:
    name = (system or platform.system()).lower()
    arch = (machine or platform.machine()).lower()
    return name, _MACHINES.get(arch, arch)


def venv_python(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def binary_path(tools: Path, name: str) -> Path:
    return tools / (f"{name}.exe" if os.name == "nt" else name)


def _first_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[0] if lines else ""


def _last_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    errors = [line for line in lines if "error" in line.lower()]
    return (errors or lines or [""])[-1]


def _output(result: Completed) -> str:
    # The last error line carries the actual failure for tracebacks and pip alike.
    return _last_line(result.stderr) or _last_line(result.stdout) or f"exit {result.returncode}"


def tree_digest(run: Runner, repo: Path, sha: str) -> tuple[int, str]:
    """Count and hash the full tracked tree of `sha`; a verifiable anchor."""
    result = run(["git", "ls-tree", "-r", "-z", "--full-tree", sha], repo, DEFAULT_TIMEOUT_SECONDS)
    if result.returncode != 0:
        raise RuntimeError(f"git ls-tree failed: {_output(result)}")
    entries = [entry for entry in result.stdout.split("\0") if entry]
    return len(entries), hashlib.sha256(result.stdout.encode("utf-8")).hexdigest()


# --- verification -----------------------------------------------------------


def check_git(run: Runner, repo: Path, sha: str) -> list[Check]:
    shallow = run(["git", "rev-parse", "--is-shallow-repository"], repo, DEFAULT_TIMEOUT_SECONDS)
    head = run(["git", "rev-parse", "HEAD"], repo, DEFAULT_TIMEOUT_SECONDS)
    status = run(["git", "status", "--porcelain"], repo, DEFAULT_TIMEOUT_SECONDS)
    clean = status.returncode == 0 and not status.stdout.strip()
    return [
        Check(
            "git_full_history",
            shallow.returncode == 0 and shallow.stdout.strip() == "false",
            {"false": "full history", "true": "shallow clone"}.get(
                shallow.stdout.strip(), _output(shallow)
            ),
        ),
        Check(
            "git_exact_revision",
            head.returncode == 0 and head.stdout.strip() == sha,
            f"HEAD {head.stdout.strip() or _output(head)}, expected {sha}",
        ),
        Check(
            "git_clean_tree",
            clean,
            "clean" if clean else (_first_line(status.stdout) or _output(status)),
        ),
    ]


def check_python(run: Runner, python: Path) -> Check:
    result = run(
        [str(python), "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"],
        None,
        DEFAULT_TIMEOUT_SECONDS,
    )
    version = result.stdout.strip()
    try:
        parts = tuple(int(part) for part in version.split(".")[:2])
    except ValueError:
        parts = ()
    passed = result.returncode == 0 and len(parts) == 2 and parts >= REQUIRED_PYTHON
    return Check("python_runtime", passed, version or _output(result))


def check_requirements(run: Runner, python: Path, repo: Path) -> Check:
    """Every hash-pinned requirement is installed at its pinned version."""
    result = run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--dry-run",
            "--quiet",
            "--disable-pip-version-check",
            "--require-hashes",
            "--report",
            "-",
            "-r",
            str(repo / REQUIREMENTS_PATH),
        ],
        repo,
        INSTALL_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        return Check("dev_requirements", False, _output(result))
    try:
        pending = json.loads(result.stdout).get("install", [])
    except (json.JSONDecodeError, AttributeError):
        return Check("dev_requirements", False, "unparseable pip report")
    if pending:
        names = ", ".join(str(item.get("metadata", {}).get("name", "?")) for item in pending)
        return Check("dev_requirements", False, f"not installed as pinned: {names}")
    return Check("dev_requirements", True, "all pinned requirements satisfied")


def check_command(run: Runner, name: str, argv: Sequence[str], expect: str = "") -> Check:
    result = run(argv, None, DEFAULT_TIMEOUT_SECONDS)
    output = result.stdout.strip()
    passed = result.returncode == 0 and bool(output) and expect in output
    detail = next((line for line in output.splitlines() if expect and expect in line), "")
    return Check(f"tool_{name}", passed, detail or _first_line(output) or _output(result))


def check_browser(run: Runner, python: Path, repo: Path) -> Check:
    result = run([str(python), "-c", RENDER_PROBE], repo, DEFAULT_TIMEOUT_SECONDS)
    detail = "render probe measured the test SVG" if result.returncode == 0 else _output(result)
    return Check("render_browser", result.returncode == 0, detail)


def check_hooks(repo: Path) -> Check:
    missing = []
    for hook in HOOKS:
        path = repo / ".git" / "hooks" / hook
        if not path.is_file() or (os.name != "nt" and not os.access(path, os.X_OK)):
            missing.append(hook)
    detail = "installed" if not missing else f"missing: {', '.join(missing)}"
    return Check("git_hooks", not missing, detail)


# --- provisioning -----------------------------------------------------------


def ensure_clone(run: Runner, source: str, repo: Path, sha: str) -> list[str]:
    actions: list[str] = []
    if not (repo / ".git").exists():
        result = run(
            ["git", "clone", "--no-checkout", source, str(repo)], None, INSTALL_TIMEOUT_SECONDS
        )
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed: {_output(result)}")
        actions.append("full clone")
    shallow = run(["git", "rev-parse", "--is-shallow-repository"], repo, DEFAULT_TIMEOUT_SECONDS)
    if shallow.stdout.strip() == "true":
        result = run(["git", "fetch", "--unshallow", "origin"], repo, INSTALL_TIMEOUT_SECONDS)
        if result.returncode != 0:
            raise RuntimeError(f"cannot unshallow the clone: {_output(result)}")
        still = run(["git", "rev-parse", "--is-shallow-repository"], repo, DEFAULT_TIMEOUT_SECONDS)
        if still.stdout.strip() != "false":
            raise RuntimeError("clone is still shallow: the source itself lacks full history")
        actions.append("unshallow")
    exists = run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], repo, DEFAULT_TIMEOUT_SECONDS)
    if exists.returncode != 0:
        result = run(["git", "fetch", "origin", sha], repo, INSTALL_TIMEOUT_SECONDS)
        if result.returncode != 0:
            raise RuntimeError(f"target commit not available from source: {_output(result)}")
        actions.append("fetch target commit")
    result = run(["git", "checkout", "--detach", sha], repo, DEFAULT_TIMEOUT_SECONDS)
    if result.returncode != 0:
        raise RuntimeError(f"checkout of {sha} failed: {_output(result)}")
    return actions


def ensure_venv(run: Runner, venv: Path, repo: Path) -> list[str]:
    actions: list[str] = []
    python = venv_python(venv)
    if not python.exists():
        result = run([sys.executable, "-m", "venv", str(venv)], None, INSTALL_TIMEOUT_SECONDS)
        if result.returncode != 0:
            raise RuntimeError(f"venv creation failed: {_output(result)}")
        actions.append("virtual environment")
    result = run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--require-hashes",
            "-r",
            str(repo / REQUIREMENTS_PATH),
        ],
        repo,
        INSTALL_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pinned requirements install failed: {_output(result)}")
    actions.append("pinned development requirements")
    return actions


def _extract(name: str, archive_name: str, payload: bytes) -> bytes:
    if archive_name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            return archive.read(f"{name}.exe")
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        member = archive.extractfile(name)
        if member is None:
            raise RuntimeError(f"{name} binary missing from release archive")
        return member.read()


def ensure_binary(
    binary: PinnedBinary, tools: Path, fetch: Downloader, key: tuple[str, str] | None = None
) -> list[str]:
    target = binary_path(tools, binary.name)
    if target.exists():
        return []
    platform_id = key or platform_key()
    asset = binary.assets.get(platform_id)
    if asset is None:
        raise RuntimeError(f"no pinned {binary.name} {binary.version} build for {platform_id}")
    archive_name, expected = asset
    payload = fetch(binary.base_url + archive_name)
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise RuntimeError(f"{binary.name} archive SHA-256 mismatch: {actual}, expected {expected}")
    tools.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_extract(binary.name, archive_name, payload))
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return [f"{binary.name} {binary.version} (SHA-256 verified)"]


def ensure_browser(run: Runner, python: Path, repo: Path) -> list[str]:
    if check_browser(run, python, repo).passed:
        return []
    result = run(
        [str(python), "-m", "playwright", "install", "chromium"], repo, INSTALL_TIMEOUT_SECONDS
    )
    if result.returncode != 0:
        raise RuntimeError(f"render browser install failed: {_output(result)}")
    return ["playwright chromium"]


def ensure_hooks(repo: Path) -> list[str]:
    actions = []
    for hook, source in HOOKS.items():
        target = repo / ".git" / "hooks" / hook
        if target.is_file():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / source, target)
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        actions.append(f"hook {hook}")
    return actions


# --- orchestration ----------------------------------------------------------


@dataclass
class Attestation:
    schema: str
    command: str
    created_at_utc: str
    source: str
    target_sha: str
    environment: dict[str, str]
    tree: dict[str, object]
    tools: dict[str, str]
    provisioning: list[str]
    checks: list[dict[str, object]]
    ready: bool


def verify_environment(run: Runner, workdir: Path, sha: str) -> tuple[list[Check], dict[str, str]]:
    repo, python, tools = workdir / "repo", venv_python(workdir / "venv"), workdir / "tools"
    checks = check_git(run, repo, sha)
    checks.append(check_python(run, python))
    checks.append(check_requirements(run, python, repo))
    commands = [(tool, [str(python), "-m", tool, "--version"], "") for tool in PYTHON_TOOLS]
    commands += [
        (binary.name, [str(binary_path(tools, binary.name)), *binary.version_args], binary.version)
        for binary in PINNED_BINARIES
    ]
    commands += [(name, list(argv), "") for name, argv in HOST_TOOLS.items()]
    versions: dict[str, str] = {}
    for name, argv, expect in commands:
        check = check_command(run, name, argv, expect)
        checks.append(check)
        if check.passed:
            versions[name] = check.detail
    checks.append(check_browser(run, python, repo))
    checks.append(check_hooks(repo))
    return checks, versions


def _provision(
    run: Runner, fetch: Downloader, source: str, workdir: Path, sha: str
) -> tuple[list[str], list[Check]]:
    repo, venv, tools = workdir / "repo", workdir / "venv", workdir / "tools"
    workdir.mkdir(parents=True, exist_ok=True)
    steps: list[tuple[str, Callable[[], list[str]]]] = [
        ("provision_clone", lambda: ensure_clone(run, source, repo, sha)),
        ("provision_venv", lambda: ensure_venv(run, venv, repo)),
    ]
    for binary in PINNED_BINARIES:
        steps.append(
            (f"provision_{binary.name}", functools.partial(ensure_binary, binary, tools, fetch))
        )
    steps += [
        ("provision_browser", lambda: ensure_browser(run, venv_python(venv), repo)),
        ("provision_hooks", lambda: ensure_hooks(repo)),
    ]
    actions: list[str] = []
    for name, step in steps:
        try:
            actions.extend(step())
        except (RuntimeError, OSError, ValueError) as exc:
            return actions, [Check(name, False, str(exc))]
    return actions, []


def attest(
    command: str,
    source: str,
    workdir: Path,
    sha: str,
    *,
    run: Runner = run_command,
    fetch: Downloader = download,
) -> Attestation:
    if len(sha) != 40 or any(char not in "0123456789abcdef" for char in sha):
        raise ValueError(f"target SHA must be 40 lowercase hex characters: {sha!r}")
    provisioning: list[str] = []
    checks: list[Check] = []
    versions: dict[str, str] = {}
    if command == "prepare":
        provisioning, checks = _provision(run, fetch, source, workdir, sha)
    if not checks:
        checks, versions = verify_environment(run, workdir, sha)
    ready = bool(checks) and all(check.passed for check in checks)
    tree: dict[str, object] = {}
    if ready:
        entries, digest = tree_digest(run, workdir / "repo", sha)
        tree = {"entries": entries, "sha256": digest}
    return Attestation(
        schema=SCHEMA,
        command=command,
        created_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        source=sanitize_source(source),
        target_sha=sha,
        environment={
            "os": platform.platform(),
            "machine": platform.machine(),
            "runner_python": platform.python_version(),
        },
        tree=tree,
        tools=versions,
        provisioning=provisioning,
        checks=[asdict(check) for check in checks],
        ready=ready,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare and attest a full-audit environment")
    parser.add_argument("command", choices=("prepare", "verify"))
    parser.add_argument("--sha", required=True, help="exact 40-character commit to audit")
    parser.add_argument(
        "--workdir", required=True, type=Path, help="directory for repo/, venv/, tools/"
    )
    parser.add_argument("--source", default="", help="git URL or path to clone (prepare only)")
    parser.add_argument(
        "--attestation", type=Path, help="default: <workdir>/environment_attestation.json"
    )
    args = parser.parse_args(argv)
    if args.command == "prepare" and not args.source:
        parser.error("prepare requires --source")
    workdir = args.workdir.resolve()
    result = attest(args.command, args.source, workdir, args.sha)
    output = args.attestation or workdir / "environment_attestation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for check in result.checks:
        print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}: {check['detail']}")
    print(f"ready: {str(result.ready).lower()} -> {output}")
    if not result.ready:
        print("Audit environment is not ready: the audit must not start.", file=sys.stderr)
    return 0 if result.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
