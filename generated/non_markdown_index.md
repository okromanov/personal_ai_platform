<!-- generated file: do not edit manually -->
---
id: generated_non_markdown_index
type: generated_document
generation_state: generated
version: 1.0
---

# Индекс файлов вне Markdown

| Параметр | Значение |
|---|---|
| Всего файлов | `142` |

> Все не-Markdown файлы репозитория, кроме `generated/`. Markdown-документы — в [`markdown_index.md`](markdown_index.md).

| Файл | Задача | Описание |
|---|---|---|
| [`.claude/settings.json`](../.claude/settings.json) | — | Реестр периодических и блокирующих quality-проверок репозитория. |
| [`.claude/skills/pre_commit_hook.sh`](../.claude/skills/pre_commit_hook.sh) | — | Канонический pre-commit hook: версии authority-документов, dev-инструменты, быстрый набор проверок, регенерация дашбордов. |
| [`.claude/skills/pre_push_hook.sh`](../.claude/skills/pre_push_hook.sh) | — | Канонический pre-push hook: полный набор проверок (mypy, форматирование, покрытие, Bandit, Vulture, анализ AST) перед отправкой изменений. |
| [`.github/workflows/project_check.yml`](../.github/workflows/project_check.yml) | — | CI-пайплайн GitHub Actions: полная проверка репозитория на каждый push, PR и еженедельно. |
| [`.gitignore`](../.gitignore) | — | Список путей и масок, исключённых из git. |
| [`operations/__init__.py`](../operations/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/hooks/__init__.py`](../operations/hooks/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/hooks/pre_commit_hook.sh`](../operations/hooks/pre_commit_hook.sh) | — | Обёртка: запускает канонический hook .claude/skills/pre_commit_hook.sh. |
| [`operations/hooks/pre_commit_regenerate_dashboards.sh`](../operations/hooks/pre_commit_regenerate_dashboards.sh) | — | Шаг pre-commit hook: при изменении любого .md-файла бампит его версию и регенерирует project_status.md, tasks.md и generated/*. |
| [`operations/hooks/pre_push_hook.sh`](../operations/hooks/pre_push_hook.sh) | — | Обёртка: запускает канонический hook .claude/skills/pre_push_hook.sh. |
| [`operations/project_config.json`](../operations/project_config.json) | — | Общие настройки репозитория: часовой пояс и адрес на GitHub. |
| [`operations/quality/requirements_dev.txt`](../operations/quality/requirements_dev.txt) | — | Зафиксированные версии dev-инструментов для локального и серверного quality suite. |
| [`operations/quality_baseline.json`](../operations/quality_baseline.json) | — | Эталонный список известных ошибок mypy: gate не даёт их числу расти. |
| [`operations/quality_registry.json`](../operations/quality_registry.json) | — | Реестр профилей качества по этапам: какие проверки обязательны для каждого milestone. |
| [`operations/scripts/__init__.py`](../operations/scripts/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/scripts/acceptance/__init__.py`](../operations/scripts/acceptance/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/scripts/acceptance/apply.py`](../operations/scripts/acceptance/apply.py) | — | Переводит этап из in-progress в completed по команде владельца и фиксирует decision_sha. |
| [`operations/scripts/common/__init__.py`](../operations/scripts/common/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/scripts/common/project.py`](../operations/scripts/common/project.py) | — | Общие утилиты репозитория: поиск корня проекта, атомарная запись файлов, обход отслеживаемых файлов, запуск команд. |
| [`operations/scripts/common/status_types.py`](../operations/scripts/common/status_types.py) | — | Общие типы данных для milestone/TASK/TEST, которыми обмениваются модули status и tasks. |
| [`operations/scripts/documents/__init__.py`](../operations/scripts/documents/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/scripts/documents/auto_generate_tasks.py`](../operations/scripts/documents/auto_generate_tasks.py) | — | Автоматическое создание TASK документов для новых архитектурных компонентов. |
| [`operations/scripts/documents/check.py`](../operations/scripts/documents/check.py) | — | Главный проверяющий скрипт репозитория: запускает все структурные и смысловые проверки. |
| [`operations/scripts/documents/generate.py`](../operations/scripts/documents/generate.py) | — | Главный генератор: пересобирает все производные файлы из состояния репозитория. |
| [`operations/scripts/documents/index.py`](../operations/scripts/documents/index.py) | — | Строит generated/markdown_index.md — перечень всех Markdown-документов репозитория. |
| [`operations/scripts/documents/links.py`](../operations/scripts/documents/links.py) | — | Проверяет, что ссылки и якоря в Markdown-документах ведут на существующие файлы и разделы. |
| [`operations/scripts/documents/metadata.py`](../operations/scripts/documents/metadata.py) | — | Разбор YAML-фронтматтера Markdown-документов. |
| [`operations/scripts/documents/non_markdown_index.py`](../operations/scripts/documents/non_markdown_index.py) | — | Строит generated/non_markdown_index.md — перечень не-Markdown файлов репозитория. |
| [`operations/scripts/documents/repository_tree.py`](../operations/scripts/documents/repository_tree.py) | — | Строит generated/repository_structure.md — полное дерево отслеживаемых файлов. |
| [`operations/scripts/documents/test_catalog.py`](../operations/scripts/documents/test_catalog.py) | — | Строит generated/test_catalog.md — каталог всех unit-тестов с описаниями. |
| [`operations/scripts/documents/traceability.py`](../operations/scripts/documents/traceability.py) | — | Строит generated/traceability_matrix.md — таблицу связей требований, компонентов, TASK и TEST. |
| [`operations/scripts/evidence/__init__.py`](../operations/scripts/evidence/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/scripts/evidence/generate_bundle.py`](../operations/scripts/evidence/generate_bundle.py) | — | Собирает evidence bundle из результатов проверок и тестов для приложения к PR. |
| [`operations/scripts/evidence/record.py`](../operations/scripts/evidence/record.py) | — | Определяет, какие цели должны быть покрыты доказательствами по quality_registry.json. |
| [`operations/scripts/github/__init__.py`](../operations/scripts/github/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/scripts/github/post_pr_comment.py`](../operations/scripts/github/post_pr_comment.py) | — | Публикует результаты проверок комментарием к Pull Request на GitHub. |
| [`operations/scripts/health_check/__init__.py`](../operations/scripts/health_check/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/scripts/health_check/generate.py`](../operations/scripts/health_check/generate.py) | — | Генерирует generated/health_check_report.md — отчёт о состоянии репозитория. |
| [`operations/scripts/health_check/metrics.py`](../operations/scripts/health_check/metrics.py) | — | Собирает метрики репозитория: git-статистику, тесты, качество кода. |
| [`operations/scripts/health_check/reporter.py`](../operations/scripts/health_check/reporter.py) | — | Форматирует собранные метрики health check в готовый Markdown-отчёт. |
| [`operations/scripts/milestones/__init__.py`](../operations/scripts/milestones/__init__.py) | — | Управление жизненным циклом этапов (milestone). |
| [`operations/scripts/milestones/init_milestone.py`](../operations/scripts/milestones/init_milestone.py) | — | Инициализирует файлы этапа при переходе planned → in-progress. |
| [`operations/scripts/milestones/start.py`](../operations/scripts/milestones/start.py) | — | Атомарный переход этапа из planned в in-progress с проверкой готовности. |
| [`operations/scripts/milestones/update_completion_report.py`](../operations/scripts/milestones/update_completion_report.py) | — | Пересобирает work/mXX_final_report.md из фактического состояния репозитория после принятия этапа. |
| [`operations/scripts/quality/__init__.py`](../operations/scripts/quality/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/scripts/quality/action_practicality.py`](../operations/scripts/quality/action_practicality.py) | — | Проверяет практическую выполнимость действия владельца: не больше 3 шагов, однозначная команда. |
| [`operations/scripts/quality/check_coverage.py`](../operations/scripts/quality/check_coverage.py) | — | Проверяет общее, критическое и diff-покрытие тестами. |
| [`operations/scripts/quality/code_analyzer.py`](../operations/scripts/quality/code_analyzer.py) | — | Анализ качества кода через AST: заглушки, незакрытые TODO, мёртвый код. |
| [`operations/scripts/quality/paths_validation.py`](../operations/scripts/quality/paths_validation.py) | — | Проверяет пути в allowed_paths карточек TASK: существование и покрытие реальным содержимым. |
| [`operations/scripts/quality/record_quality_suite.py`](../operations/scripts/quality/record_quality_suite.py) | — | Записывает результат прогона CI quality suite как доказательство для коммита. |
| [`operations/scripts/quality/registry.py`](../operations/scripts/quality/registry.py) | — | Загружает и проверяет operations/quality_registry.json. |
| [`operations/scripts/quality/run_mypy_baseline.py`](../operations/scripts/quality/run_mypy_baseline.py) | — | Запускает mypy и сверяет число ошибок с сохранённым baseline. |
| [`operations/scripts/quality/run_suite.py`](../operations/scripts/quality/run_suite.py) | — | Канонический раннер: последовательно запускает весь набор проверок качества. |
| [`operations/scripts/quality/run_unittests.py`](../operations/scripts/quality/run_unittests.py) | — | Канонический запуск unit-тестов: падает при любом пропущенном (skipped) тесте. |
| [`operations/scripts/quality/test_coverage.py`](../operations/scripts/quality/test_coverage.py) | — | Проверяет, что каждое тестируемое требование этапа покрыто хотя бы одной карточкой TEST. |
| [`operations/scripts/requirements/__init__.py`](../operations/scripts/requirements/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/scripts/requirements/apply_requirements.py`](../operations/scripts/requirements/apply_requirements.py) | — | Применяет результат requirement_wizard: создаёт документы требований в репозитории. |
| [`operations/scripts/requirements/requirement_wizard.py`](../operations/scripts/requirements/requirement_wizard.py) | — | Интерактивный wizard для создания требований и задач из одного бизнес-требования. |
| [`operations/scripts/requirements/stage_planning_wizard.py`](../operations/scripts/requirements/stage_planning_wizard.py) | — | Интерактивный wizard для планирования следующего этапа проекта. |
| [`operations/scripts/status/__init__.py`](../operations/scripts/status/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/scripts/status/generate_project_status.py`](../operations/scripts/status/generate_project_status.py) | — | Собирает данные для project_status.md: этапы, задачи, прогресс, действие владельца. |
| [`operations/scripts/status/human_status.py`](../operations/scripts/status/human_status.py) | [`TASK_004`](../work/tasks/task_004_arc_004.md) | Рендерит project_status.md — сводку для владельца без внутренних технических деталей. |
| [`operations/scripts/status/technical_status.py`](../operations/scripts/status/technical_status.py) | — | Формирует техническую сводку состояния репозитория для отладки, не для владельца. |
| [`operations/scripts/tasks/__init__.py`](../operations/scripts/tasks/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/scripts/tasks/check_change_scope.py`](../operations/scripts/tasks/check_change_scope.py) | — | Проверка покрытия путей поставки проекта карточками TASK. |
| [`operations/scripts/tasks/generate.py`](../operations/scripts/tasks/generate.py) | — | Собирает карточки TASK и рендерит tasks.md. |
| [`operations/scripts/tasks/semantics.py`](../operations/scripts/tasks/semantics.py) | — | Смысловая проверка связей TASK → компонент → требование. |
| [`operations/scripts/traceability/__init__.py`](../operations/scripts/traceability/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/scripts/traceability/auto_link.py`](../operations/scripts/traceability/auto_link.py) | — | Автоматическое заполнение связей трассировки между документами требований. |
| [`operations/scripts/traceability/full_traceability.py`](../operations/scripts/traceability/full_traceability.py) | — | Сквозные инварианты трассируемости, дополняющие структурные проверки связей. |
| [`operations/scripts/traceability/semantic_consistency.py`](../operations/scripts/traceability/semantic_consistency.py) | — | Смысловые проверки связей, которые нельзя выявить только синтаксисом. |
| [`operations/scripts/versioning/increment_file_version.py`](../operations/scripts/versioning/increment_file_version.py) | — | Автоматически повышает версию файла при изменении содержимого. |
| [`operations/tests/__init__.py`](../operations/tests/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/tests/integration/__init__.py`](../operations/tests/integration/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/tests/integration/test_quality_pipeline.py`](../operations/tests/integration/test_quality_pipeline.py) | — | Интеграционные тесты: совместная работа нескольких проверок качества. |
| [`operations/tests/performance/__init__.py`](../operations/tests/performance/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/tests/performance/test_critical_paths.py`](../operations/tests/performance/test_critical_paths.py) | — | Тесты производительности критичных, часто вызываемых функций. |
| [`operations/tests/product/__init__.py`](../operations/tests/product/__init__.py) | [`TASK_001`](../work/tasks/task_001_arc_001.md) | Пустой файл-маркер Python-пакета. |
| [`operations/tests/product/test_channels.py`](../operations/tests/product/test_channels.py) | [`TASK_001`](../work/tasks/task_001_arc_001.md) | Unit-тесты компонента Channels (ARC_CMP_001). |
| [`operations/tests/product/test_model_gateway.py`](../operations/tests/product/test_model_gateway.py) | [`TASK_004`](../work/tasks/task_004_arc_004.md) | — |
| [`operations/tests/product/test_orchestration.py`](../operations/tests/product/test_orchestration.py) | [`TASK_003`](../work/tasks/task_003_arc_003.md) | — |
| [`operations/tests/product/test_owner_control.py`](../operations/tests/product/test_owner_control.py) | [`TASK_002`](../work/tasks/task_002_arc_002.md) | — |
| [`operations/tests/stress/__init__.py`](../operations/tests/stress/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/tests/stress/test_scalability.py`](../operations/tests/stress/test_scalability.py) | — | Стресс-тесты масштабируемости функций, перебирающих этапы, задачи или файлы. |
| [`operations/tests/test_acceptance.py`](../operations/tests/test_acceptance.py) | — | Тесты процедуры принятия этапа (acceptance). |
| [`operations/tests/test_acceptance_cli_edges.py`](../operations/tests/test_acceptance_cli_edges.py) | — | Тесты граничных случаев CLI и вспомогательных функций процедуры принятия. |
| [`operations/tests/test_acceptance_transition.py`](../operations/tests/test_acceptance_transition.py) | — | Тесты перехода этапа в состояние completed. |
| [`operations/tests/test_boundary_cases.py`](../operations/tests/test_boundary_cases.py) | — | Тесты граничных случаев парсинга и валидации недоверенных данных. |
| [`operations/tests/test_checker_negative_paths.py`](../operations/tests/test_checker_negative_paths.py) | — | Тесты отрицательных сценариев главного проверяющего скрипта check.py. |
| [`operations/tests/test_concurrency.py`](../operations/tests/test_concurrency.py) | — | Тесты безопасности при параллельном доступе. |
| [`operations/tests/test_durability.py`](../operations/tests/test_durability.py) | — | Тесты надёжности примитива атомарной записи файлов (atomic_write). |
| [`operations/tests/test_generation_safety.py`](../operations/tests/test_generation_safety.py) | — | Тесты безопасности генераторов производных файлов. |
| [`operations/tests/test_governance_hardening.py`](../operations/tests/test_governance_hardening.py) | — | Тесты, закрепляющие правила управления репозиторием. |
| [`operations/tests/test_lifecycle_matrix.py`](../operations/tests/test_lifecycle_matrix.py) | — | Тесты матрицы состояний жизненного цикла TASK/TEST/этапов. |
| [`operations/tests/test_owner_usability.py`](../operations/tests/test_owner_usability.py) | [`TASK_004`](../work/tasks/task_004_arc_004.md) | Тесты удобства project_status.md для владельца: обязательные элементы, без внутренних деталей. |
| [`operations/tests/test_quality_integration.py`](../operations/tests/test_quality_integration.py) | — | Интеграционные тесты сквозного прогона quality suite. |
| [`operations/tests/test_scope_coverage.py`](../operations/tests/test_scope_coverage.py) | — | Тесты покрытия путей поставки карточками TASK. |
| [`operations/tests/test_security_extended.py`](../operations/tests/test_security_extended.py) | — | Тесты безопасности сверх governance-проверок: секреты, права доступа. |
| [`operations/tests/tooling/__init__.py`](../operations/tests/tooling/__init__.py) | — | Пустой файл-маркер Python-пакета. |
| [`operations/tests/tooling/test_auxiliary_quality_tools.py`](../operations/tests/tooling/test_auxiliary_quality_tools.py) | — | Тесты вспомогательных инструментов: авто-создание TASK, авто-связывание трассировки. |
| [`operations/tests/tooling/test_change_scope.py`](../operations/tests/tooling/test_change_scope.py) | — | Тесты проверки scope изменений и честности метаданных документов. |
| [`operations/tests/tooling/test_code_analyzer.py`](../operations/tests/tooling/test_code_analyzer.py) | — | — |
| [`operations/tests/tooling/test_coverage_policy.py`](../operations/tests/tooling/test_coverage_policy.py) | — | Тесты политики покрытия тестами: общее, по модулям, diff. |
| [`operations/tests/tooling/test_evidence_record.py`](../operations/tests/tooling/test_evidence_record.py) | — | Тесты сборки evidence bundle по результатам проверок. |
| [`operations/tests/tooling/test_full_traceability.py`](../operations/tests/tooling/test_full_traceability.py) | — | Тесты сквозных инвариантов трассируемости. |
| [`operations/tests/tooling/test_health_check.py`](../operations/tests/tooling/test_health_check.py) | — | Тесты сбора git- и code-quality метрик для health check отчёта. |
| [`operations/tests/tooling/test_links.py`](../operations/tests/tooling/test_links.py) | — | Тесты проверки ссылок и якорей в Markdown-документах. |
| [`operations/tests/tooling/test_markdown_index.py`](../operations/tests/tooling/test_markdown_index.py) | — | — |
| [`operations/tests/tooling/test_metadata_parsing.py`](../operations/tests/tooling/test_metadata_parsing.py) | — | Тесты парсинга YAML-фронтматтера документов. |
| [`operations/tests/tooling/test_milestone_lifecycle.py`](../operations/tests/tooling/test_milestone_lifecycle.py) | — | Тесты инициализации и завершения этапа (milestone). |
| [`operations/tests/tooling/test_milestone_start_and_task_semantics.py`](../operations/tests/tooling/test_milestone_start_and_task_semantics.py) | — | Тесты атомарного старта этапа и смысловой проверки TASK. |
| [`operations/tests/tooling/test_non_markdown_index.py`](../operations/tests/tooling/test_non_markdown_index.py) | — | Тесты генератора generated/non_markdown_index.md. |
| [`operations/tests/tooling/test_project_common.py`](../operations/tests/tooling/test_project_common.py) | — | Тесты общих утилит репозитория: git-информация, чтение текстовых файлов. |
| [`operations/tests/tooling/test_quality_baseline.py`](../operations/tests/tooling/test_quality_baseline.py) | — | Тесты сверки mypy с сохранённым baseline ошибок. |
| [`operations/tests/tooling/test_quality_registry.py`](../operations/tests/tooling/test_quality_registry.py) | — | Тесты валидации реестра профилей качества. |
| [`operations/tests/tooling/test_quality_runner.py`](../operations/tests/tooling/test_quality_runner.py) | — | Тесты канонического раннера quality suite. |
| [`operations/tests/tooling/test_requirement_tooling.py`](../operations/tests/tooling/test_requirement_tooling.py) | — | Тесты wizard'ов создания требований и планирования этапа. |
| [`operations/tests/tooling/test_semantic_consistency.py`](../operations/tests/tooling/test_semantic_consistency.py) | — | Тесты смысловых проверок связей документов. |
| [`operations/tests/tooling/test_task_registry.py`](../operations/tests/tooling/test_task_registry.py) | — | Тесты сбора карточек TASK и ширины их идентификаторов. |
| [`operations/tests/tooling/test_test_catalog.py`](../operations/tests/tooling/test_test_catalog.py) | — | Тесты генератора generated/test_catalog.md. |
| [`operations/tests/tooling/test_traceability.py`](../operations/tests/tooling/test_traceability.py) | — | Тесты построения generated/traceability_matrix.md. |
| [`operations/tests/tooling/test_versioning.py`](../operations/tests/tooling/test_versioning.py) | — | Тесты автоматического повышения версии файла. |
| [`pyproject.toml`](../pyproject.toml) | — | Конфигурация ruff, mypy и порогов покрытия тестами. |
| [`src/__init__.py`](../src/__init__.py) | [`TASK_001`](../work/tasks/task_001_arc_001.md) | Исходный код personal_ai_platform: реализует архитектурные компоненты ARC_CMP_001–009. |
| [`src/channels/__init__.py`](../src/channels/__init__.py) | [`TASK_001`](../work/tasks/task_001_arc_001.md) | Точка входа пакета Channels: экспортирует Channel, TaskMessage и TelegramChannel. |
| [`src/channels/base.py`](../src/channels/base.py) | [`TASK_001`](../work/tasks/task_001_arc_001.md) | Базовый контракт канала: нормализует ввод/вывод в TaskMessage с отслеживаемым статусом. |
| [`src/channels/telegram.py`](../src/channels/telegram.py) | [`TASK_001`](../work/tasks/task_001_arc_001.md) | Реализация канала Telegram: нормализует сообщения Telegram в формат TaskMessage. |
| [`src/models/__init__.py`](../src/models/__init__.py) | [`TASK_004`](../work/tasks/task_004_arc_004.md) | — |
| [`src/models/base.py`](../src/models/base.py) | [`TASK_004`](../work/tasks/task_004_arc_004.md) | — |
| [`src/models/runtime_adapter.py`](../src/models/runtime_adapter.py) | [`TASK_004`](../work/tasks/task_004_arc_004.md) | — |
| [`src/models/stub_gateway.py`](../src/models/stub_gateway.py) | [`TASK_004`](../work/tasks/task_004_arc_004.md) | — |
| [`src/orchestration/__init__.py`](../src/orchestration/__init__.py) | [`TASK_003`](../work/tasks/task_003_arc_003.md) | — |
| [`src/orchestration/orchestrator.py`](../src/orchestration/orchestrator.py) | [`TASK_003`](../work/tasks/task_003_arc_003.md) | — |
| [`src/orchestration/runtime_port.py`](../src/orchestration/runtime_port.py) | [`TASK_003`](../work/tasks/task_003_arc_003.md) | — |
| [`src/orchestration/stub_runtime.py`](../src/orchestration/stub_runtime.py) | [`TASK_003`](../work/tasks/task_003_arc_003.md) | — |
| [`src/owner_control/__init__.py`](../src/owner_control/__init__.py) | [`TASK_002`](../work/tasks/task_002_arc_002.md) | — |
| [`src/owner_control/base.py`](../src/owner_control/base.py) | [`TASK_002`](../work/tasks/task_002_arc_002.md) | — |
| [`src/owner_control/control.py`](../src/owner_control/control.py) | [`TASK_002`](../work/tasks/task_002_arc_002.md) | — |
| [`src/owner_control/emergency_switch.py`](../src/owner_control/emergency_switch.py) | [`TASK_002`](../work/tasks/task_002_arc_002.md) | — |
| [`work/acceptance/.gitkeep`](../work/acceptance/.gitkeep) | — | Пустой файл-плейсхолдер, сохраняющий пустую папку в git. |
| [`work/acceptance/m01.json`](../work/acceptance/m01.json) | — | Запись о принятии этапа m01: решение владельца, дата и SHA коммита. |
| [`work/tasks/.gitkeep`](../work/tasks/.gitkeep) | — | Пустой файл-плейсхолдер, сохраняющий пустую папку в git. |
