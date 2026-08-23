"""Интерактивный wizard для создания полного набора требований и задач из одного бизнес-требования."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import find_project_root


@dataclass
class RequirementContext:
    """Контекст для сбора информации о требовании."""

    milestone: str  # "m02", "m03", etc
    br_id: str
    br_title: str
    br_description: str
    category: str  # "integration", "storage", "ui", "automation", "security"
    integrations: list[str]  # ["telegram", "github", "email"]
    data_types: list[str]  # ["user_data", "documents", "config"]
    security_level: str  # "public", "internal", "sensitive"
    external_systems: list[str]  # ["telegram", "github_api"]
    performance_needs: list[str]  # ["realtime", "batch", "cached"]
    arch_components: list[str]  # ["web_server", "database", "queue"]
    potential_threats: list[str]  # auto-identified
    user_story: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)


THREAT_PATTERNS = {
    "integration": [
        "Несанкционированный доступ через внешний сервис",
        "Утечка данных при передаче",
        "Injection атаки через интеграцию",
    ],
    "storage": [
        "Несанкционированный доступ к данным",
        "Потеря данных",
        "Утечка конфиденциальной информации",
    ],
    "ui": [
        "XSS атаки",
        "CSRF атаки",
        "Фишинг через интерфейс",
    ],
    "automation": [
        "Неожиданное автоматическое действие",
        "Отказ в обслуживании",
        "Escalation привилегий",
    ],
    "security": [
        "Обход аутентификации",
        "Брутфорс атаки",
        "Timing атаки",
    ],
}

SECURITY_CONTROLS = {
    "Несанкционированный доступ": ["Аутентификация", "Авторизация", "Аудит доступа"],
    "Утечка данных": ["Шифрование в пути", "Шифрование в покое", "Контроль доступа"],
    "Injection атаки": ["Input validation", "Parameterized queries", "WAF"],
    "XSS атаки": ["Content Security Policy", "Output encoding", "Input validation"],
    "CSRF атаки": ["CSRF tokens", "SameSite cookies"],
    "Потеря данных": ["Резервное копирование", "Репликация", "Восстановление"],
    "Отказ в обслуживании": ["Rate limiting", "Load balancing", "Monitoring"],
}

ARCHITECTURE_PATTERNS = {
    "integration": ["API Gateway", "Message Queue", "Rate Limiter"],
    "storage": ["Database", "Cache", "Search Index"],
    "ui": ["Web Server", "CDN", "Session Manager"],
    "automation": ["Task Queue", "Scheduler", "State Machine"],
    "security": ["Auth Service", "Vault", "Audit Logger"],
}


def _ask_question(question: str, question_type: str = "text") -> Any:
    """Ask user a question and return the answer."""
    print(f"\n❓ {question}")

    if question_type == "text":
        return input("→ ").strip()
    elif question_type == "multiline":
        print("   (Введите текст, затем пустую строку для завершения)")
        lines = []
        while True:
            line = input("→ ").strip()
            if not line:
                break
            lines.append(line)
        return "\n".join(lines)
    elif question_type == "list":
        print("   (Через запятую, или Enter для пропуска)")
        return [x.strip() for x in input("→ ").split(",") if x.strip()]
    elif question_type == "choice":
        # question_type передаёт варианты через |
        return input("→ ").strip().lower()

    return ""


def collect_requirement_info() -> RequirementContext:
    """Collect requirement information through interactive dialog."""

    print("\n" + "=" * 60)
    print("🧙 WIZARD: Создание полного набора требований")
    print("=" * 60)

    # 0. Выбор этапа
    print("\n📍 ШАГ 0: На какой этап добавляется требование?")
    print("   (Введите название вашего этапа, напр. m02, m03, m04...)")
    milestone = _ask_question("Выберите этап:", "text").lower()
    if not milestone:
        milestone = "m02"
    print(f"   ✅ Выбран этап: {milestone}")

    # 1. Основное бизнес-требование
    print("\n📋 ШАГ 1: Основное требование")
    br_id = _ask_question("ID требования (BR_XXX):", "text")
    br_title = _ask_question("Краткое название (1 строка):", "text")
    br_description = _ask_question("Полное описание (что именно нужно):", "multiline")
    user_story = _ask_question("User story (опционально, что делает пользователь):", "text")

    # 2. Категоризация
    print("\n🏷️  ШАГ 2: Тип требования")
    print("   Варианты: integration | storage | ui | automation | security")
    category = _ask_question("Выберите категорию:", "text").lower()
    if category not in THREAT_PATTERNS:
        category = "integration"

    # 3. Детали интеграций и данных
    print("\n🔌 ШАГ 3: Технические детали")
    integrations = _ask_question("Внешние системы (telegram, github, email, и т.д.):", "list")
    data_types = _ask_question("Типы данных (user_data, documents, config, и т.д.):", "list")

    # 4. Уровень безопасности
    print("\n🔐 ШАГ 4: Безопасность")
    print("   Варианты: public | internal | sensitive")
    security_level = _ask_question("Уровень конфиденциальности данных:", "text")
    if security_level not in ["public", "internal", "sensitive"]:
        security_level = "internal"

    # 5. Производительность
    print("\n⚡ ШАГ 5: Производительность")
    print("   Варианты: realtime | batch | cached")
    performance_needs = _ask_question("Требования к производительности:", "list")

    # Идентифицировать угрозы на основе категории
    potential_threats = THREAT_PATTERNS.get(category, [])

    context = RequirementContext(
        milestone=milestone,
        br_id=br_id.upper(),
        br_title=br_title,
        br_description=br_description,
        category=category,
        integrations=integrations,
        data_types=data_types,
        security_level=security_level,
        external_systems=integrations,
        performance_needs=performance_needs,
        potential_threats=potential_threats,
        user_story=user_story,
        arch_components=ARCHITECTURE_PATTERNS.get(category, []),
    )

    # Подтверждение
    print("\n✅ Собранная информация:")
    print(f"   Этап: {context.milestone.upper()}")
    print(f"   BR: {context.br_id} — {context.br_title}")
    print(f"   Категория: {context.category}")
    print(f"   Интеграции: {', '.join(context.integrations) or 'нет'}")
    print(f"   Уровень защиты: {context.security_level}")
    print(f"   Угрозы: {len(context.potential_threats)} идентифицировано")

    return context


def generate_system_requirements(context: RequirementContext) -> list[dict[str, str]]:
    """Generate SYS_* requirements from BR context."""
    sys_reqs = []

    # Базовое системное требование
    sys_reqs.append(
        {
            "id": f"SYS_{context.br_id[3:]}",
            "title": f"Реализовать {context.br_title}",
            "description": context.br_description,
            "type": "functional",
            "priority": "core",
        }
    )

    # Требования на основе интеграций
    if context.integrations:
        for integration in context.integrations:
            sys_reqs.append(
                {
                    "id": f"SYS_{int(context.br_id[3:]) + 100}",  # Плейсхолдер, нужна реальная нумерация
                    "title": f"Интеграция с {integration}",
                    "description": f"Обеспечить подключение к {integration}",
                    "type": "functional",
                    "priority": "core",
                }
            )

    # Требования на основе безопасности
    if context.security_level in ["sensitive", "internal"]:
        sys_reqs.append(
            {
                "id": f"SYS_{int(context.br_id[3:]) + 200}",
                "title": f"Защита данных ({context.security_level})",
                "description": f"Обеспечить защиту {context.security_level} данных",
                "type": "non-functional",
                "priority": "core",
            }
        )

    return sys_reqs


def generate_threats_and_controls(
    context: RequirementContext,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate THR_* and SEC_CTL_* from identified threats."""
    threats: list[dict[str, Any]] = []
    controls: list[dict[str, Any]] = []

    for threat_desc in context.potential_threats:
        threat_id = f"THR_{len(threats) + 1:03d}"
        threats.append(
            {
                "id": threat_id,
                "title": threat_desc,
                "description": f"Угроза при реализации {context.br_title}: {threat_desc}",
                "affects": context.br_id,
            }
        )

        # Добавить соответствующие меры защиты
        for control_type, control_list in SECURITY_CONTROLS.items():
            if control_type.lower() in threat_desc.lower():
                for control_name in control_list:
                    controls.append(
                        {
                            "id": f"SEC_CTL_{len(controls) + 1:03d}",
                            "title": control_name,
                            "description": f"Мера защиты от угрозы: {threat_desc}",
                            "mitigates": threat_id,
                        }
                    )

    return threats, controls


def generate_architecture_components(context: RequirementContext) -> list[dict[str, Any]]:
    """Generate ARC_* components for the requirement."""
    components: list[dict[str, Any]] = []

    for comp_name in context.arch_components:
        components.append(
            {
                "id": f"ARC_{len(components) + 1:03d}",
                "title": comp_name,
                "description": f"Компонент {comp_name} для реализации {context.br_title}",
                "responsibility": f"Обеспечить {comp_name.replace('_', ' ').lower()}",
            }
        )

    return components


def generate_test_documents(context: RequirementContext, sys_count: int) -> list[dict[str, Any]]:
    """Generate TEST_* documents for verification."""
    tests: list[dict[str, Any]] = []

    # Один тест на основное требование
    tests.append(
        {
            "id": f"TEST_{1000 + len(tests) + 1}",
            "title": f"Проверка {context.br_title}",
            "verifies": context.br_id,
            "description": "Проверить, что требование реализовано согласно спецификации",
        }
    )

    # Тесты на системные требования
    for i in range(sys_count):
        tests.append(
            {
                "id": f"TEST_{1000 + len(tests) + 1}",
                "title": f"Проверка системного требования {i + 1}",
                "verifies": f"SYS_{context.br_id[3:]}",
                "description": "Проверить функциональность",
            }
        )

    return tests


def generate_task_documents(context: RequirementContext, arch_count: int) -> list[dict]:
    """Generate TASK_* documents for implementation."""
    tasks = []

    for i, component in enumerate(context.arch_components):
        tasks.append(
            {
                "id": f"TASK_{2000 + i + 1}",
                "title": f"Реализация {component}",
                "implements": f"ARC_{i + 1:03d}",
                "description": f"Разработать компонент {component}",
            }
        )

    return tasks


def interactive_requirement_wizard(root: Path) -> dict[str, Any]:
    """Run interactive wizard and return generated artifacts."""

    context = collect_requirement_info()

    print("\n🔄 Генерация артефактов...")

    sys_reqs = generate_system_requirements(context)
    threats, controls = generate_threats_and_controls(context)
    arch_components = generate_architecture_components(context)
    tests = generate_test_documents(context, len(sys_reqs))
    tasks = generate_task_documents(context, len(arch_components))

    result = {
        "milestone": context.milestone,
        "br": {
            "id": context.br_id,
            "title": context.br_title,
            "description": context.br_description,
            "category": context.category,
            "user_story": context.user_story,
        },
        "sys_requirements": sys_reqs,
        "threats": threats,
        "security_controls": controls,
        "architecture": arch_components,
        "tests": tests,
        "tasks": tasks,
        "summary": {
            "sys_count": len(sys_reqs),
            "threat_count": len(threats),
            "control_count": len(controls),
            "arch_count": len(arch_components),
            "test_count": len(tests),
            "task_count": len(tasks),
        },
    }

    return result


if __name__ == "__main__":
    root = find_project_root(Path.cwd())
    result = interactive_requirement_wizard(root)

    print("\n" + "=" * 60)
    print("📊 ИТОГИ ГЕНЕРАЦИИ")
    print("=" * 60)
    print(f"✅ SYS требований: {result['summary']['sys_count']}")
    print(f"✅ Угроз идентифицировано: {result['summary']['threat_count']}")
    print(f"✅ Мер защиты: {result['summary']['control_count']}")
    print(f"✅ Архитектурных компонентов: {result['summary']['arch_count']}")
    print(f"✅ TEST документов: {result['summary']['test_count']}")
    print(f"✅ TASK документов: {result['summary']['task_count']}")
    print("\n💾 Результат сохранён в памяти агента и готов к применению.")
    print("   Используйте: python operations/scripts/requirements/apply_requirements.py")
