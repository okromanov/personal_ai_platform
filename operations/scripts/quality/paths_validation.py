#!/usr/bin/env python3.12
"""Валидация путей в allowed_paths карточек TASK.

Проверяет:
- Все пути в allowed_paths существуют (файлы или папки)
- Пути правильно указаны (не содержат ошибок в написании)
- Массовые пути (путь/**) охватывают реальное содержимое
"""

from __future__ import annotations

import re
import sys
from fnmatch import fnmatch
from pathlib import Path


def get_all_tracked_paths(root: Path) -> set[str]:
    """Получить все пути в репозитории (кроме .git и generated)."""
    tracked = set()

    for path in root.rglob("*"):
        if ".git" in path.parts or "generated" in path.parts:
            continue

        relative = path.relative_to(root)
        tracked.add(str(relative))

    return tracked


def validate_task_paths(root: Path) -> list[str]:
    """Валидировать allowed_paths в карточках TASK."""
    errors: list[str] = []

    tasks_dir = root / "work/tasks"
    if not tasks_dir.exists():
        return errors

    all_paths = get_all_tracked_paths(root)

    for task_file in tasks_dir.glob("task_*.md"):
        content = task_file.read_text(encoding="utf-8-sig")

        # Найти section allowed_paths:
        allowed_match = re.search(r"^allowed_paths:\s*\n((?:\s+-.*\n)*)", content, re.MULTILINE)

        if not allowed_match:
            continue

        allowed_text = allowed_match.group(1)
        allowed_paths = re.findall(r"-\s+(.+)", allowed_text)

        for allowed_path in allowed_paths:
            # An entry may carry a trailing " — description" (a per-file
            # Russian description written once for project_status.md);
            # only the path itself is a real filesystem path to validate.
            allowed_path = allowed_path.split(" — ", 1)[0]
            allowed_path = allowed_path.strip().strip('"').strip("'")

            # Проверить, содержит ли маски
            if "*" in allowed_path or "?" in allowed_path:
                # Это маска, проверить, есть ли файлы, которые подходят
                matches = [p for p in all_paths if fnmatch(p, allowed_path)]
                if not matches:
                    errors.append(
                        f"{task_file.name}: маска '{allowed_path}' не соответствует "
                        f"ни одному файлу в репозитории"
                    )
            else:
                # Это конкретный путь, проверить, существует ли
                full_path = root / allowed_path

                if not full_path.exists():
                    # Попробовать найти похожий путь (может быть опечатка)
                    similar = [
                        p
                        for p in all_paths
                        if allowed_path.lower() in p.lower() or p.lower() in allowed_path.lower()
                    ]

                    if similar:
                        errors.append(
                            f"{task_file.name}: путь '{allowed_path}' не существует "
                            f"(похожие: {', '.join(similar[:2])})"
                        )
                    else:
                        errors.append(
                            f"{task_file.name}: путь '{allowed_path}' не существует в репозитории"
                        )

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    errors = validate_task_paths(root)

    if errors:
        print("❌ Ошибки в allowed_paths:")
        for error in sorted(errors):
            print(f"  {error}")
        return 1

    print("✅ Все пути в allowed_paths корректны")
    return 0


if __name__ == "__main__":
    sys.exit(main())
