"""Shared console prompting primitives for repository wizards."""

from typing import Any


def ask_question(question: str, question_type: str = "text") -> Any:
    """Ask one supported console question and return its normalized answer."""
    print(f"\n❓ {question}")
    if question_type == "text":
        return input("→ ").strip()
    if question_type == "multiline":
        print("   (Введите текст, затем пустую строку для завершения)")
        lines = []
        while True:
            line = input("→ ").strip()
            if not line:
                break
            lines.append(line)
        return "\n".join(lines)
    if question_type == "list":
        print("   (Через запятую, или Enter для пропуска)")
        return [item.strip() for item in input("→ ").split(",") if item.strip()]
    if question_type == "choice":
        return input("→ ").strip().lower()
    if question_type == "checkbox":
        print("   (Несколько вариантов, через пробел: 0 1 2 / через запятую: a, b, c)")
        return [item.strip() for item in input("→ ").replace(",", " ").split() if item.strip()]
    raise ValueError(f"unsupported question type: {question_type}")
