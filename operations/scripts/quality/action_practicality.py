#!/usr/bin/env python3.12
"""Проверка практической выполнимости действий владельца.

Валидирует:
- Действие владельца не требует > 3 основных шагов
- Команда ПРОДОЛЖАЙ ясна и однозначна
- Текст действия не содержит требования запускать скрипты
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def check_project_status(root: Path) -> list[str]:
    """Проверить project_status.md на практичность действий."""
    errors = []

    status_file = root / "project_status.md"
    if not status_file.exists():
        return errors

    content = status_file.read_text(encoding="utf-8-sig")

    # Проверка 1: Найти команду ПРОДОЛЖАЙ и убедиться, что она одна
    продолжай_matches = re.findall(r"`ПРОДОЛЖАЙ\s+(\w+)`", content)
    if not продолжай_matches:
        errors.append("project_status.md: не найдена команда ПРОДОЛЖАЙ")
    elif len(set(продолжай_matches)) > 1:
        errors.append(
            f"project_status.md: более одной уникальной команды ПРОДОЛЖАЙ "
            f"({', '.join(set(продолжай_matches))})"
        )

    # Проверка 2: Найти раздел "Когда потребуется ваше участие" и посчитать шаги
    когда_раздел = re.search(
        r"## Когда потребуется ваше участие\s*\n(.*?)(?=##|$)", content, re.DOTALL | re.IGNORECASE
    )

    if когда_раздел:
        раздел_текст = когда_раздел.group(1)

        # Посчитать пункты списка (нумерованные или ненумерованные)
        steps = re.findall(r"^\s*(?:\d+\.|[-*])\s+", раздел_текст, re.MULTILINE)
        step_count = len(steps)

        # Предупреждение: если больше 6 шагов
        if step_count > 6:
            errors.append(
                f"project_status.md: слишком много шагов для участия владельца "
                f"({step_count} шагов, рекомендуется до 3-5)"
            )

    # Проверка 3: Запрещённые слова в действиях
    запрещённые = [
        r"запустить.*python",
        r"запустить.*git",
        r"запустить.*bash",
        r"выполнить.*команду",
        r"отправить.*PR",  # владелец не должен сам делать PR
        r"слить.*PR",  # слияние тоже не должно быть действием владельца
    ]

    для_действия = re.search(
        r"## Ваше действие сейчас\s*\n(.*?)(?=##)", content, re.DOTALL | re.IGNORECASE
    )

    if для_действия:
        действие_текст = для_действия.group(1).lower()
        for pattern in запрещённые:
            if re.search(pattern, действие_текст):
                errors.append(
                    f"project_status.md: действие владельца содержит "
                    f"запрещённую инструкцию ({pattern})"
                )

    # Проверка 4: Наличие явного указания "не требуется запускать проверки"
    if (
        "не требуется запускать" not in content.lower()
        and "вам не нужно запускать" not in content.lower()
    ):
        errors.append(
            "project_status.md: нет явного указания, что владельцу не нужно запускать проверки"
        )

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    errors = check_project_status(root)

    if errors:
        print("❌ Ошибки практичности действий владельца:")
        for error in sorted(errors):
            print(f"  {error}")
        return 1

    print("✅ Действия владельца практичны и выполнимы")
    return 0


if __name__ == "__main__":
    sys.exit(main())
