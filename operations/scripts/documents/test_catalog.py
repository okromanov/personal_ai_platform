"""Render generated/test_catalog.md: a per-test catalog with descriptions.

Reuses the same unittest discovery mechanism as
operations/scripts/quality/run_unittests.py (the canonical test runner), so
the catalog always lists exactly the tests that actually run in CI - never a
stale or hand-maintained approximation of them.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from operations.scripts.documents.repository_tree import GENERATED_HEADER

TRIGGER = "push / pull_request / merge_group / manual dispatch (CI, both jobs)"
CATEGORY_LABELS = {
    "core": "Core logic (acceptance, governance, lifecycle)",
    "tooling": "Tooling (quality scripts, registries, traceability)",
    "integration": "Integration (quality pipeline end-to-end)",
    "performance": "Performance regression",
    "stress": "Stress / scalability",
    "product": "Product",
}
CATEGORY_ORDER = ["core", "tooling", "integration", "performance", "stress", "product"]


def _humanize(method_name: str) -> str:
    return method_name.removeprefix("test_").replace("_", " ").strip().capitalize()


def _category(module_dotted: str) -> str:
    if "." in module_dotted:
        head = module_dotted.split(".", 1)[0]
        if head in CATEGORY_LABELS:
            return head
    return "core"


def _iter_tests(suite: unittest.TestSuite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _iter_tests(item)
        else:
            yield item


def collect_tests(root: Path, start_dir: str = "operations/tests") -> list[dict[str, str]]:
    discovery_root = (root / start_dir).resolve()
    loader = unittest.TestLoader()
    suite = loader.discover(
        str(discovery_root), pattern="test_*.py", top_level_dir=str(discovery_root)
    )

    rows: list[dict[str, str]] = []
    for test in _iter_tests(suite):
        test_id = test.id()
        module_dotted, class_name, method_name = test_id.rsplit(".", 2)
        method = getattr(test, method_name)
        doc_lines = (method.__doc__ or "").strip().splitlines()
        description = doc_lines[0].strip() if doc_lines else _humanize(method_name)
        rows.append(
            {
                "category": _category(module_dotted),
                "file": f"{start_dir}/{module_dotted.replace('.', '/')}.py",
                "class": class_name,
                "method": method_name,
                "description": description,
            }
        )
    rows.sort(
        key=lambda r: (
            CATEGORY_ORDER.index(r["category"]) if r["category"] in CATEGORY_ORDER else 99,
            r["file"],
            r["class"],
            r["method"],
        )
    )
    return rows


def render_test_catalog(root: Path, generated_date: str | None = None) -> str:
    rows = collect_tests(root)
    total = len(rows)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["category"]] = counts.get(row["category"], 0) + 1

    lines = [
        GENERATED_HEADER,
        "---",
        "id: generated_test_catalog",
        "type: generated_report",
        "generation_state: generated",
        "version: 1.0",
        "---",
        "",
        "# Каталог тестов",
        "",
        "| Параметр | Значение |",
        "|---|---|",
        f"| Всего тестов | `{total}` |",
    ]
    for category in CATEGORY_ORDER:
        if category in counts:
            lines.append(f"| {CATEGORY_LABELS[category]} | `{counts[category]}` |")
    lines.extend(
        [
            "",
            f"> Все тесты обнаруживаются рекурсивно из `operations/tests/` через "
            f"`operations/scripts/quality/run_unittests.py` и запускаются по единому триггеру: "
            f"{TRIGGER}. Локальный `pre-commit` запускает быстрый профиль без coverage; "
            f"`pre-push` (опционально) и CI запускают полный профиль.",
            "",
            "| Категория | Файл | Класс | Тест | Описание |",
            "|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {CATEGORY_LABELS[row['category']]} | `{row['file']}` | `{row['class']}` | "
            f"`{row['method']}` | {row['description']} |"
        )
    return "\n".join(lines) + "\n"
