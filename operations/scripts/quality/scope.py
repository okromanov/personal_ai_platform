"""Canonical Python path scopes shared by local, CI and health checks."""

PYTHON_SOURCE_PATHS = ("operations/scripts", "src")
PYTHON_TEST_PATHS = ("operations/tests",)
PYTHON_QUALITY_PATHS = (*PYTHON_SOURCE_PATHS, *PYTHON_TEST_PATHS)
