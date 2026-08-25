"""Unit tests for the compute runtime environment (INF_CMP_001).

Runs under the canonical `operations/scripts/quality/run_unittests.py`
discovery, so it is part of the enforced CI gate.

A real `docker build` of the root `Dockerfile` cannot be exercised here
(no Docker daemon in this environment) -- this suite instead covers what
is verifiable without one: the health-check CLI's own behavior, and a
static structural check that the Dockerfile actually declares the
properties INF_CMP_001 requires (pinned base image, non-root user,
health check, identifiable version).
"""

from __future__ import annotations

import io
import json
import os
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from src.operations.health import DependencyStatus, HealthAggregator
from src.operations.health_check import build_health_aggregator, main

REPO_ROOT = Path(__file__).resolve().parents[3]


class HealthCheckCliTests(unittest.TestCase):
    def test_build_health_aggregator_returns_an_aggregator(self) -> None:
        self.assertIsInstance(build_health_aggregator(), HealthAggregator)

    def test_main_exits_zero_and_reports_healthy_with_no_registered_checks(self) -> None:
        with redirect_stdout(io.StringIO()) as out:
            exit_code = main()

        self.assertEqual(exit_code, 0)
        payload = json.loads(out.getvalue())
        self.assertTrue(payload["healthy"])
        self.assertEqual(payload["dependencies"], [])

    def test_main_exits_nonzero_when_a_registered_check_is_unhealthy(self) -> None:
        aggregator = HealthAggregator()
        aggregator.register("db", lambda: DependencyStatus(name="db", healthy=False, detail="down"))
        with (
            mock.patch(
                "src.operations.health_check.build_health_aggregator", return_value=aggregator
            ),
            redirect_stdout(io.StringIO()) as out,
        ):
            exit_code = main()

        self.assertEqual(exit_code, 1)
        payload = json.loads(out.getvalue())
        self.assertFalse(payload["healthy"])
        self.assertEqual(
            payload["dependencies"], [{"name": "db", "healthy": False, "detail": "down"}]
        )

    def test_main_reports_the_app_version_from_the_environment(self) -> None:
        with (
            mock.patch.dict(os.environ, {"APP_VERSION": "1.2.3"}),
            redirect_stdout(io.StringIO()) as out,
        ):
            main()

        payload = json.loads(out.getvalue())
        self.assertEqual(payload["version"], "1.2.3")

    def test_main_reports_unknown_version_when_unset(self) -> None:
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            redirect_stdout(io.StringIO()) as out,
        ):
            main()

        payload = json.loads(out.getvalue())
        self.assertEqual(payload["version"], "unknown")


class DockerfileStructureTests(unittest.TestCase):
    """Static checks a Docker daemon is not needed to run.

    Not a substitute for an actual `docker build` -- that verification is
    left to a real Docker-capable environment (CI or the owner's
    machine), since this sandbox has no running daemon.
    """

    def setUp(self) -> None:
        self.dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")

    def test_base_image_is_pinned_to_a_supported_python_version(self) -> None:
        self.assertRegex(self.dockerfile, r"(?m)^FROM python:3\.12-slim\b")

    def test_runs_as_a_non_root_application_user(self) -> None:
        self.assertIn("useradd", self.dockerfile)
        self.assertRegex(self.dockerfile, r"(?m)^USER app\b")

    def test_declares_a_health_check(self) -> None:
        self.assertIn("HEALTHCHECK", self.dockerfile)
        self.assertIn("src.operations.health_check", self.dockerfile)

    def test_accepts_an_identifiable_version_build_argument(self) -> None:
        self.assertIn("ARG APP_VERSION", self.dockerfile)
        self.assertIn("ENV APP_VERSION=${APP_VERSION}", self.dockerfile)

    def test_dockerignore_excludes_version_control_and_caches(self) -> None:
        dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
        self.assertIn(".git", dockerignore)
        self.assertIn("__pycache__", dockerignore)


if __name__ == "__main__":
    unittest.main()
