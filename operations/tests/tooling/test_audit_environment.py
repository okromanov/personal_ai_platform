from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import tarfile
import tempfile
import unittest
import zipfile
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from operations.scripts.audit import prepare_environment as env
from operations.scripts.audit.prepare_environment import Completed

ROOT = Path(__file__).resolve().parents[3]
BINARIES = {binary.name: binary for binary in env.PINNED_BINARIES}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _source_repo(root: Path) -> tuple[Path, str]:
    source = root / "source"
    source.mkdir()
    _git(source, "init", "-q", "-b", "main")
    _git(source, "config", "user.email", "audit@example.invalid")
    _git(source, "config", "user.name", "Audit")
    for index in range(2):
        (source / f"file_{index}.txt").write_text(f"{index}\n", encoding="utf-8")
        _git(source, "add", ".")
        _git(source, "commit", "-q", "-m", f"commit {index}")
    return source, _git(source, "rev-parse", "HEAD")


class FakeTools:
    """Real git; scripted results for every other command, by argv substring."""

    def __init__(self, overrides: dict[str, Completed] | None = None) -> None:
        self.calls: list[list[str]] = []
        self.overrides = overrides or {}

    def __call__(self, argv: Sequence[str], cwd: Path | None, timeout: int) -> Completed:
        argv = list(argv)
        self.calls.append(argv)
        if argv[0] == "git":
            return env.run_command(argv, cwd, timeout)
        joined = " ".join(argv)
        for fragment, result in self.overrides.items():
            if fragment in joined:
                return result
        if "sys.version_info" in joined:
            return Completed(0, "3.12.9\n", "")
        if "--dry-run" in argv:
            return Completed(0, json.dumps({"install": []}), "")
        tool = Path(argv[0]).stem
        if tool in BINARIES:
            return Completed(0, f"Version: {BINARIES[tool].version}\n", "")
        if "--version" in argv or tool == "docker":
            return Completed(0, f"{argv[-2] if '-m' in argv else tool} 1.0\n", "")
        return Completed(0, "", "")


def _tarball(name: str, binary: bytes) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        info = tarfile.TarInfo(name)
        info.size = len(binary)
        archive.addfile(info, io.BytesIO(binary))
    return buffer.getvalue()


def _test_binary(name: str, payload: bytes, key: tuple[str, str]) -> env.PinnedBinary:
    asset = (f"{name}_test.tar.gz", hashlib.sha256(payload).hexdigest())
    return replace(BINARIES[name], assets={key: asset})


class SanitizeAndPlatformTests(unittest.TestCase):
    def test_credentials_are_removed_from_source_url(self) -> None:
        self.assertEqual(
            env.sanitize_source("https://user:token@example.org/repo.git"),
            "https://example.org/repo.git",
        )
        self.assertEqual(env.sanitize_source("/srv/repo"), "/srv/repo")

    def test_platform_names_are_normalised(self) -> None:
        self.assertEqual(env.platform_key("Windows", "AMD64"), ("windows", "x64"))
        self.assertEqual(env.platform_key("Linux", "aarch64"), ("linux", "arm64"))
        self.assertEqual(env.platform_key("Darwin", "arm64"), ("darwin", "arm64"))

    def test_linux_pins_match_the_ci_workflow(self) -> None:
        workflow = (ROOT / ".github/workflows/project_check.yml").read_text(encoding="utf-8")
        for name in ("gitleaks", "actionlint"):
            match = re.search(
                rf"download/v(?P<version>[\d.]+)/(?P<asset>{name}_[\d.]+_linux_\w+\.tar\.gz)\s+"
                r'echo "(?P<sha>[0-9a-f]{64})',
                workflow,
            )
            assert match is not None, name
            binary = BINARIES[name]
            self.assertEqual(match["version"], binary.version)
            self.assertEqual(binary.assets[("linux", "x64")], (match["asset"], match["sha"]))

    def test_every_pinned_binary_covers_the_owner_platforms(self) -> None:
        for binary in env.PINNED_BINARIES:
            for key in (("linux", "x64"), ("darwin", "arm64"), ("windows", "x64")):
                archive, sha256 = binary.assets[key]
                self.assertIn(binary.version, archive)
                self.assertRegex(sha256, r"^[0-9a-f]{64}$")


class GitVerificationTests(unittest.TestCase):
    def test_full_clone_at_target_sha_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source, sha = _source_repo(Path(tmp))
            repo = Path(tmp) / "repo"
            self.assertEqual(
                env.ensure_clone(env.run_command, str(source), repo, sha), ["full clone"]
            )
            checks = env.check_git(env.run_command, repo, sha)
            self.assertTrue(all(check.passed for check in checks), checks)

    def test_shallow_clone_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source, sha = _source_repo(Path(tmp))
            repo = Path(tmp) / "shallow"
            subprocess.run(
                ["git", "clone", "-q", "--depth", "1", source.as_uri(), str(repo)], check=True
            )
            checks = {check.name: check for check in env.check_git(env.run_command, repo, sha)}
            self.assertFalse(checks["git_full_history"].passed)
            self.assertEqual(checks["git_full_history"].detail, "shallow clone")

    def test_wrong_revision_and_dirty_tree_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source, sha = _source_repo(Path(tmp))
            _git(source, "checkout", "-q", "HEAD~1")
            (source / "file_0.txt").write_text("edited\n", encoding="utf-8")
            checks = {check.name: check for check in env.check_git(env.run_command, source, sha)}
            self.assertFalse(checks["git_exact_revision"].passed)
            self.assertFalse(checks["git_clean_tree"].passed)

    def test_shallow_clone_is_unshallowed_during_provisioning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source, sha = _source_repo(Path(tmp))
            repo = Path(tmp) / "repo"
            subprocess.run(
                ["git", "clone", "-q", "--depth", "1", source.as_uri(), str(repo)], check=True
            )
            self.assertEqual(
                env.ensure_clone(env.run_command, str(source), repo, sha), ["unshallow"]
            )
            self.assertEqual(_git(repo, "rev-parse", "--is-shallow-repository"), "false")

    def test_shallow_source_cannot_yield_full_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source, sha = _source_repo(Path(tmp))
            shallow_source = Path(tmp) / "shallow_source"
            subprocess.run(
                ["git", "clone", "-q", "--depth", "1", source.as_uri(), str(shallow_source)],
                check=True,
            )
            with self.assertRaisesRegex(RuntimeError, "still shallow"):
                env.ensure_clone(env.run_command, str(shallow_source), Path(tmp) / "repo", sha)

    def test_commit_outside_cloned_branches_is_fetched_by_sha(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source, _ = _source_repo(Path(tmp))
            _git(source, "config", "uploadpack.allowAnySHA1InWant", "true")
            _git(source, "checkout", "-q", "-b", "side")
            _git(source, "commit", "-q", "--allow-empty", "-m", "side only")
            side = _git(source, "rev-parse", "HEAD")
            _git(source, "update-ref", "refs/audit/side", side)
            _git(source, "checkout", "-q", "main")
            _git(source, "branch", "-q", "-D", "side")
            repo = Path(tmp) / "repo"
            actions = env.ensure_clone(env.run_command, source.as_uri(), repo, side)
            self.assertEqual(actions, ["full clone", "fetch target commit"])
            self.assertEqual(_git(repo, "rev-parse", "HEAD"), side)

    def test_tree_digest_counts_every_tracked_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source, sha = _source_repo(Path(tmp))
            entries, digest = env.tree_digest(env.run_command, source, sha)
            self.assertEqual(entries, 2)
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertEqual(env.tree_digest(env.run_command, source, sha)[1], digest)
            with self.assertRaises(RuntimeError):
                env.tree_digest(env.run_command, source, "0" * 40)

    def test_unreachable_source_fails_provisioning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "git clone failed"):
                env.ensure_clone(
                    env.run_command, str(Path(tmp) / "absent"), Path(tmp) / "r", "0" * 40
                )


class ToolVerificationTests(unittest.TestCase):
    def test_python_below_minimum_is_rejected(self) -> None:
        old = FakeTools({"sys.version_info": Completed(0, "3.11.9\n", "")})
        self.assertFalse(env.check_python(old, Path("python")).passed)
        self.assertTrue(env.check_python(FakeTools(), Path("python")).passed)

    def test_requirement_not_installed_as_pinned_is_rejected(self) -> None:
        pending = json.dumps({"install": [{"metadata": {"name": "ruff"}}]})
        check = env.check_requirements(
            FakeTools({"--dry-run": Completed(0, pending, "")}), Path("python"), ROOT
        )
        self.assertFalse(check.passed)
        self.assertIn("ruff", check.detail)
        broken = FakeTools({"--dry-run": Completed(0, "not json", "")})
        self.assertFalse(env.check_requirements(broken, Path("python"), ROOT).passed)
        failing = FakeTools({"--dry-run": Completed(1, "", "ERROR: No matching distribution")})
        self.assertIn("No matching", env.check_requirements(failing, Path("python"), ROOT).detail)
        self.assertTrue(env.check_requirements(FakeTools(), Path("python"), ROOT).passed)

    def test_pinned_binary_must_report_its_pinned_version(self) -> None:
        wrong = FakeTools({"gitleaks": Completed(0, "8.0.0\n", "")})
        check = env.check_command(wrong, "gitleaks", ["gitleaks", "version"], "8.30.1")
        self.assertFalse(check.passed)
        right = FakeTools({"gitleaks": Completed(0, "8.30.1\n", "")})
        self.assertTrue(
            env.check_command(right, "gitleaks", ["gitleaks", "version"], "8.30.1").passed
        )

    def test_missing_host_tool_is_reported(self) -> None:
        missing = FakeTools({"shellcheck": Completed(127, "", "No such file: shellcheck")})
        check = env.check_command(missing, "shellcheck", ["shellcheck", "--version"])
        self.assertFalse(check.passed)
        self.assertIn("shellcheck", check.detail)

    def test_hooks_must_be_installed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            for source in env.HOOKS.values():
                (repo / source).parent.mkdir(parents=True, exist_ok=True)
                (repo / source).write_text("#!/bin/sh\n", encoding="utf-8")
            self.assertFalse(env.check_hooks(repo).passed)
            self.assertEqual(len(env.ensure_hooks(repo)), 2)
            self.assertTrue(env.check_hooks(repo).passed)
            self.assertEqual(env.ensure_hooks(repo), [])


class ProvisioningTests(unittest.TestCase):
    def test_pinned_archive_is_verified_before_install(self) -> None:
        payload = _tarball("actionlint", b"binary")
        key = ("linux", "x64")
        binary = _test_binary("actionlint", payload, key)
        with tempfile.TemporaryDirectory() as tmp:
            tools = Path(tmp) / "tools"
            self.assertEqual(len(env.ensure_binary(binary, tools, lambda _url: payload, key)), 1)
            self.assertEqual(env.binary_path(tools, "actionlint").read_bytes(), b"binary")
            self.assertEqual(env.ensure_binary(binary, tools, lambda _url: b"", key), [])

    def test_tampered_archive_is_refused(self) -> None:
        gitleaks = BINARIES["gitleaks"]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
                env.ensure_binary(gitleaks, Path(tmp), lambda _url: b"tampered", ("linux", "x64"))
            self.assertFalse(env.binary_path(Path(tmp), "gitleaks").exists())
            with self.assertRaisesRegex(RuntimeError, "no pinned gitleaks"):
                env.ensure_binary(gitleaks, Path(tmp), lambda _url: b"", ("plan9", "x64"))

    def test_archive_without_the_binary_is_refused(self) -> None:
        with self.assertRaises(KeyError):
            env._extract("syft", "syft.tar.gz", _tarball("README", b"text"))

    def test_windows_zip_archive_yields_the_exe(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("syft.exe", b"exe")
        self.assertEqual(env._extract("syft", "syft.zip", buffer.getvalue()), b"exe")

    def test_browser_is_installed_only_when_probe_fails(self) -> None:
        self.assertEqual(env.ensure_browser(FakeTools(), Path("python"), ROOT), [])
        broken = FakeTools(
            {"measure_svg_elements": Completed(1, "", "Error: Executable doesn't exist")}
        )
        self.assertEqual(env.ensure_browser(broken, Path("python"), ROOT), ["playwright chromium"])
        self.assertIn(["python", "-m", "playwright", "install", "chromium"], broken.calls)
        refused = FakeTools(
            {
                "measure_svg_elements": Completed(1, "", "no browser"),
                "playwright install": Completed(1, "", "offline"),
            }
        )
        with self.assertRaisesRegex(RuntimeError, "offline"):
            env.ensure_browser(refused, Path("python"), ROOT)

    def test_download_refuses_plain_http(self) -> None:
        with self.assertRaises(ValueError):
            env.download("http://example.org/gitleaks.tar.gz")


class FailurePathTests(unittest.TestCase):
    def test_missing_program_and_timeout_become_results(self) -> None:
        missing = env.run_command(["definitely-not-a-real-program-xyz"])
        self.assertEqual(missing.returncode, 127)
        slow = env.run_command([env.sys.executable, "-c", "import time; time.sleep(5)"], None, 1)
        self.assertEqual(slow.returncode, 124)
        self.assertIn("timeout", slow.stderr)

    def test_download_rejects_redirect_away_from_https(self) -> None:
        class Response:
            def __init__(self, url: str) -> None:
                self.url = url

            def __enter__(self) -> Response:
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def geturl(self) -> str:
                return self.url

            def read(self) -> bytes:
                return b"payload"

        class Opener:
            def __init__(self, final_url: str) -> None:
                self.final_url = final_url

            def open(self, url: str, timeout: int) -> Response:
                return Response(self.final_url)

        with patch.object(env.urllib.request, "build_opener", return_value=Opener("https://x/y")):
            self.assertEqual(env.download("https://example.org/a"), b"payload")
        with patch.object(env.urllib.request, "build_opener", return_value=Opener("http://x/y")):
            with self.assertRaisesRegex(ValueError, "redirected"):
                env.download("https://example.org/a")

    def test_unparseable_python_version_is_rejected(self) -> None:
        garbage = FakeTools({"sys.version_info": Completed(0, "three.twelve\n", "")})
        self.assertFalse(env.check_python(garbage, Path("python")).passed)

    def test_git_provisioning_failures_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source, sha = _source_repo(Path(tmp))
            repo = Path(tmp) / "repo"
            env.ensure_clone(env.run_command, str(source), repo, sha)
            scenarios = {
                "cannot unshallow": {
                    "--is-shallow-repository": Completed(0, "true\n", ""),
                    "--unshallow": Completed(128, "", "fatal: no network"),
                },
                "target commit not available": {
                    "cat-file": Completed(1, "", ""),
                    "fetch origin": Completed(128, "", "fatal: not our ref"),
                },
                "checkout of": {"checkout": Completed(1, "", "error: pathspec")},
            }
            for message, overrides in scenarios.items():
                runner = _GitOverrides(overrides)
                with self.subTest(message), self.assertRaisesRegex(RuntimeError, message):
                    env.ensure_clone(runner, str(source), repo, sha)

    def test_virtual_environment_is_created_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            created = FakeTools()
            actions = env.ensure_venv(created, Path(tmp) / "venv", ROOT)
            self.assertEqual(actions, ["virtual environment", "pinned development requirements"])
            self.assertEqual(created.calls[0][1:3], ["-m", "venv"])
            failed = FakeTools({"-m venv": Completed(1, "", "Error: ensurepip missing")})
            with self.assertRaisesRegex(RuntimeError, "venv creation failed"):
                env.ensure_venv(failed, Path(tmp) / "other", ROOT)

    def test_directory_entry_instead_of_binary_is_refused(self) -> None:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            info = tarfile.TarInfo("syft")
            info.type = tarfile.DIRTYPE
            archive.addfile(info)
        with self.assertRaisesRegex(RuntimeError, "missing from release archive"):
            env._extract("syft", "syft.tar.gz", buffer.getvalue())


class _GitOverrides:
    """Real git except for the scripted argv fragments."""

    def __init__(self, overrides: dict[str, Completed]) -> None:
        self.overrides = overrides

    def __call__(self, argv: Sequence[str], cwd: Path | None, timeout: int) -> Completed:
        joined = " ".join(argv)
        for fragment, result in self.overrides.items():
            if fragment in joined:
                return result
        return env.run_command(argv, cwd, timeout)


class AttestationTests(unittest.TestCase):
    def _prepare(self, tmp: Path, runner: FakeTools) -> env.Attestation:
        source, _ = _source_repo(tmp)
        for hook_source in env.HOOKS.values():
            path = source / hook_source
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("#!/bin/sh\n", encoding="utf-8")
        _git(source, "add", ".")
        _git(source, "commit", "-q", "-m", "hooks")
        sha = _git(source, "rev-parse", "HEAD")
        workdir = tmp / "audit"
        env.venv_python(workdir / "venv").parent.mkdir(parents=True)
        env.venv_python(workdir / "venv").write_text("", encoding="utf-8")
        key = env.platform_key()
        payloads = {name: _tarball(name, name.encode()) for name in BINARIES}
        pinned = tuple(_test_binary(name, payloads[name], key) for name in BINARIES)
        by_asset = {binary.assets[key][0]: payloads[binary.name] for binary in pinned}
        with patch.object(env, "PINNED_BINARIES", pinned):
            return env.attest(
                "prepare",
                f"https://u:secret@{source}",
                workdir,
                sha,
                run=_LocalSource(runner, source),
                fetch=lambda url: by_asset[url.rsplit("/", 1)[1]],
            )

    def test_prepared_environment_is_ready_and_anchored_to_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self._prepare(Path(tmp), FakeTools())
            self.assertTrue(result.ready, result.checks)
            self.assertEqual(result.tree["entries"], 4)
            self.assertNotIn("secret", result.source)
            self.assertEqual(
                set(result.tools),
                {*env.PYTHON_TOOLS, *BINARIES, *env.HOST_TOOLS},
            )

    def test_any_failed_check_makes_environment_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = FakeTools({"docker": Completed(1, "", "Cannot connect to the Docker daemon")})
            result = self._prepare(Path(tmp), runner)
            self.assertFalse(result.ready)
            self.assertEqual(result.tree, {})
            failed = [check["name"] for check in result.checks if not check["passed"]]
            self.assertEqual(failed, ["tool_docker"])

    def test_failed_provisioning_stops_before_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = FakeTools(
                {"pip install --disable-pip-version-check": Completed(1, "", "network unreachable")}
            )
            result = self._prepare(Path(tmp), runner)
            self.assertFalse(result.ready)
            self.assertEqual(len(result.checks), 1)
            self.assertEqual(result.checks[0]["name"], "provision_venv")
            self.assertIn("network unreachable", str(result.checks[0]["detail"]))

    def test_invalid_sha_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            env.attest("verify", "", Path("."), "HEAD")

    def test_main_writes_attestation_and_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "att.json"
            for ready in (False, True):
                fake = env.Attestation(
                    env.SCHEMA,
                    "verify",
                    "t",
                    "",
                    "a" * 40,
                    {},
                    {},
                    {},
                    [],
                    [{"name": "x", "passed": ready, "detail": "d"}],
                    ready,
                )
                with patch.object(env, "attest", return_value=fake):
                    code = env.main(
                        ["verify", "--sha", "a" * 40, "--workdir", tmp, "--attestation", str(out)]
                    )
                self.assertEqual(code, 0 if ready else 1)
                self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["ready"], ready)
            with self.assertRaises(SystemExit):
                env.main(["prepare", "--sha", "a" * 40, "--workdir", tmp])


class _LocalSource:
    """Route the credential-bearing test URL to the local source repository."""

    def __init__(self, runner: FakeTools, source: Path) -> None:
        self.runner = runner
        self.source = source

    def __call__(self, argv: Sequence[str], cwd: Path | None, timeout: int) -> Completed:
        argv = [str(self.source) if "secret@" in part else part for part in argv]
        return self.runner(argv, cwd, timeout)


if __name__ == "__main__":
    unittest.main()
