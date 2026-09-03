from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_document_contracts(root: Path) -> dict[str, Any]:
    path = root / "operations/document_contracts.json"
    return json.loads(path.read_text(encoding="utf-8"))


_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = load_document_contracts(_ROOT)
STATE_VALUES = {key: set(value) for key, value in CONTRACTS["states"].items()}
STATE_FIELDS = tuple(STATE_VALUES)
NEXT_ACTORS = set(CONTRACTS["task"]["next_actor"])
TEST_EXECUTIONS = set(CONTRACTS["test"]["execution"])
APPLICABILITY_VALUES = set(CONTRACTS["document"]["applicability"])
DEFAULT_APPLICABILITY = str(CONTRACTS["document"]["default_applicability"])
POSIX_PYTHON = str(CONTRACTS["runtime"]["posix_python"])
WINDOWS_PYTHON = str(CONTRACTS["runtime"]["windows_python"])
