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
| Всего файлов | `125` |

> Каждая строка — один не-`.md` файл репозитория (код, конфигурация, данные), не документ: Markdown-документы перечислены в [`document_index.md`](document_index.md). «Задача» указана, только если файл входит в `allowed_paths` какой-то TASK за пределами её собственной карточки — у большинства файлов инфраструктуры репозитория такой TASK нет, это ожидаемо. «Описание» берётся из собственного источника файла (docstring модуля для `.py`, заголовочный комментарий для `.sh`) и никогда не выдумывается — для остальных типов файлов честно указано отсутствие источника.

| Файл | Задача | Описание |
|---|---|---|
| [`.claude/settings.json`](../.claude/settings.json) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`.claude/skills/pre_commit_hook.sh`](../.claude/skills/pre_commit_hook.sh) | — | Canonical pre-commit hook for personal_ai_platform. Install: cp .claude/skills/pre_commit_hook.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit |
| [`.claude/skills/pre_push_hook.sh`](../.claude/skills/pre_push_hook.sh) | — | Canonical pre-push hook for personal_ai_platform. Install: cp .claude/skills/pre_push_hook.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push Runs the same full quality profile CI enforces (mypy, Ruff format, coverage policy, Bandit, Vulture, AST code analysis) before code leaves the machine, so a regression is caught locally instead of on the next CI run. Actionlint, ShellCheck, pip-audit and Gitleaks stay CI-only: they fetch pinned external binaries over the network, which does not belong in a local git hook. |
| [`.github/workflows/project_check.yml`](../.github/workflows/project_check.yml) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`.gitignore`](../.gitignore) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/__init__.py`](../operations/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/hooks/__init__.py`](../operations/hooks/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/hooks/pre_commit_hook.sh`](../operations/hooks/pre_commit_hook.sh) | — | Compatibility entrypoint. The canonical hook lives with the repository QA playbooks. |
| [`operations/hooks/pre_commit_regenerate_dashboards.sh`](../operations/hooks/pre_commit_regenerate_dashboards.sh) | — | Pre-commit hook: regenerate dashboards if any tracked Markdown doc changed Triggered before commit to ensure project_status.md, tasks.md and generated/* stay in sync This hook is intentionally non-blocking (a failure here must not stop a commit), but non-blocking must never mean invisible: every failure is printed to stderr so the developer sees it locally instead of only in CI. |
| [`operations/hooks/pre_push_hook.sh`](../operations/hooks/pre_push_hook.sh) | — | Compatibility entrypoint. The canonical hook lives with the repository QA playbooks. |
| [`operations/project_config.json`](../operations/project_config.json) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/quality/requirements_dev.txt`](../operations/quality/requirements_dev.txt) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/quality_baseline.json`](../operations/quality_baseline.json) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/quality_registry.json`](../operations/quality_registry.json) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/__init__.py`](../operations/scripts/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/acceptance/__init__.py`](../operations/scripts/acceptance/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/acceptance/apply.py`](../operations/scripts/acceptance/apply.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/common/__init__.py`](../operations/scripts/common/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/common/project.py`](../operations/scripts/common/project.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/common/status_types.py`](../operations/scripts/common/status_types.py) | — | Shared TypedDict shapes for the project status/task/test data pipeline. |
| [`operations/scripts/documents/__init__.py`](../operations/scripts/documents/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/documents/auto_generate_tasks.py`](../operations/scripts/documents/auto_generate_tasks.py) | — | Автоматическое создание TASK документов для новых архитектурных компонентов. |
| [`operations/scripts/documents/check.py`](../operations/scripts/documents/check.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/documents/generate.py`](../operations/scripts/documents/generate.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/documents/index.py`](../operations/scripts/documents/index.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/documents/links.py`](../operations/scripts/documents/links.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/documents/metadata.py`](../operations/scripts/documents/metadata.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/documents/non_markdown_index.py`](../operations/scripts/documents/non_markdown_index.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/documents/repository_tree.py`](../operations/scripts/documents/repository_tree.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/documents/test_catalog.py`](../operations/scripts/documents/test_catalog.py) | — | Render generated/test_catalog.md: a per-test catalog with descriptions. |
| [`operations/scripts/documents/traceability.py`](../operations/scripts/documents/traceability.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/evidence/__init__.py`](../operations/scripts/evidence/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/evidence/generate_bundle.py`](../operations/scripts/evidence/generate_bundle.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/evidence/record.py`](../operations/scripts/evidence/record.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/github/__init__.py`](../operations/scripts/github/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/github/post_pr_comment.py`](../operations/scripts/github/post_pr_comment.py) | — | Generate and post validation results as a GitHub PR comment. |
| [`operations/scripts/health_check/__init__.py`](../operations/scripts/health_check/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/health_check/generate.py`](../operations/scripts/health_check/generate.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/health_check/metrics.py`](../operations/scripts/health_check/metrics.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/health_check/reporter.py`](../operations/scripts/health_check/reporter.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/milestones/__init__.py`](../operations/scripts/milestones/__init__.py) | — | Controlled milestone lifecycle operations. |
| [`operations/scripts/milestones/init_milestone.py`](../operations/scripts/milestones/init_milestone.py) | — | Initialize milestone files on transition. |
| [`operations/scripts/milestones/start.py`](../operations/scripts/milestones/start.py) | — | Atomic preflight and transition from planned to in-progress. |
| [`operations/scripts/milestones/update_completion_report.py`](../operations/scripts/milestones/update_completion_report.py) | — | Render and update work/m0X_final_report.md from real repository state. |
| [`operations/scripts/quality/__init__.py`](../operations/scripts/quality/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/quality/action_practicality.py`](../operations/scripts/quality/action_practicality.py) | — | Проверка практической выполнимости действий владельца. |
| [`operations/scripts/quality/check_coverage.py`](../operations/scripts/quality/check_coverage.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/quality/code_analyzer.py`](../operations/scripts/quality/code_analyzer.py) | — | Advanced code quality analysis using AST (Abstract Syntax Tree). |
| [`operations/scripts/quality/paths_validation.py`](../operations/scripts/quality/paths_validation.py) | — | Валидация путей в allowed_paths карточек TASK. |
| [`operations/scripts/quality/record_quality_suite.py`](../operations/scripts/quality/record_quality_suite.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/quality/registry.py`](../operations/scripts/quality/registry.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/quality/run_mypy_baseline.py`](../operations/scripts/quality/run_mypy_baseline.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/quality/run_suite.py`](../operations/scripts/quality/run_suite.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/quality/run_unittests.py`](../operations/scripts/quality/run_unittests.py) | — | Canonical unittest discovery that fails on every skipped test. |
| [`operations/scripts/quality/test_coverage.py`](../operations/scripts/quality/test_coverage.py) | — | Stage-aware coverage of testable milestone requirements by TEST specs. |
| [`operations/scripts/requirements/__init__.py`](../operations/scripts/requirements/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/requirements/apply_requirements.py`](../operations/scripts/requirements/apply_requirements.py) | — | Применить результаты requirement_wizard: создать все документы в репозитории. |
| [`operations/scripts/requirements/requirement_wizard.py`](../operations/scripts/requirements/requirement_wizard.py) | — | Интерактивный wizard для создания полного набора требований и задач из одного бизнес-требования. |
| [`operations/scripts/requirements/stage_planning_wizard.py`](../operations/scripts/requirements/stage_planning_wizard.py) | — | Интерактивный wizard для планирования следующего этапа проекта. |
| [`operations/scripts/status/__init__.py`](../operations/scripts/status/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/status/generate_project_status.py`](../operations/scripts/status/generate_project_status.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/status/human_status.py`](../operations/scripts/status/human_status.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/status/technical_status.py`](../operations/scripts/status/technical_status.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/tasks/__init__.py`](../operations/scripts/tasks/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/tasks/check_change_scope.py`](../operations/scripts/tasks/check_change_scope.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/tasks/generate.py`](../operations/scripts/tasks/generate.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/tasks/semantics.py`](../operations/scripts/tasks/semantics.py) | — | Semantic TASK-to-component-to-requirement traceability checks. |
| [`operations/scripts/traceability/__init__.py`](../operations/scripts/traceability/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/scripts/traceability/auto_link.py`](../operations/scripts/traceability/auto_link.py) | — | Автоматическое заполнение связей трассировки между документами требований. |
| [`operations/scripts/traceability/full_traceability.py`](../operations/scripts/traceability/full_traceability.py) | — | End-to-end traceability invariants that complement structural edge checks. |
| [`operations/scripts/traceability/semantic_consistency.py`](../operations/scripts/traceability/semantic_consistency.py) | — | Deterministic semantic guards for relations that syntax alone cannot validate. |
| [`operations/scripts/versioning/increment_file_version.py`](../operations/scripts/versioning/increment_file_version.py) | — | Auto-increment file version when content changes. |
| [`operations/tests/__init__.py`](../operations/tests/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/integration/__init__.py`](../operations/tests/integration/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/integration/test_quality_pipeline.py`](../operations/tests/integration/test_quality_pipeline.py) | — | Integration tests for quality check pipeline. |
| [`operations/tests/performance/__init__.py`](../operations/tests/performance/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/performance/test_critical_paths.py`](../operations/tests/performance/test_critical_paths.py) | — | Performance regression tests for critical, frequently-invoked functions. |
| [`operations/tests/product/__init__.py`](../operations/tests/product/__init__.py) | [`TASK_001`](../work/tasks/task_001_arc_001.md) | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/product/test_channels.py`](../operations/tests/product/test_channels.py) | [`TASK_001`](../work/tasks/task_001_arc_001.md) | Unit tests for the Channels component (ARC_CMP_001). |
| [`operations/tests/stress/__init__.py`](../operations/tests/stress/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/stress/test_scalability.py`](../operations/tests/stress/test_scalability.py) | — | Stress and scalability tests: verify that functions which loop over milestones, tasks, or filesystem trees behave correctly (and reasonably fast) as the input grows well beyond today's repository size. |
| [`operations/tests/test_acceptance.py`](../operations/tests/test_acceptance.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/test_acceptance_cli_edges.py`](../operations/tests/test_acceptance_cli_edges.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/test_acceptance_transition.py`](../operations/tests/test_acceptance_transition.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/test_boundary_cases.py`](../operations/tests/test_boundary_cases.py) | — | Boundary and edge-case tests for parsing/validation functions that handle untrusted or externally-influenced text: front matter parsing, confirmation strings, and text-scanning summaries. |
| [`operations/tests/test_checker_negative_paths.py`](../operations/tests/test_checker_negative_paths.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/test_concurrency.py`](../operations/tests/test_concurrency.py) | — | Concurrency safety tests. |
| [`operations/tests/test_durability.py`](../operations/tests/test_durability.py) | — | Durability tests for the atomic_write persistence primitive. |
| [`operations/tests/test_generation_safety.py`](../operations/tests/test_generation_safety.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/test_governance_hardening.py`](../operations/tests/test_governance_hardening.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/test_lifecycle_matrix.py`](../operations/tests/test_lifecycle_matrix.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/test_owner_usability.py`](../operations/tests/test_owner_usability.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/test_quality_integration.py`](../operations/tests/test_quality_integration.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/test_scope_coverage.py`](../operations/tests/test_scope_coverage.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/test_security_extended.py`](../operations/tests/test_security_extended.py) | — | Security-focused tests that go beyond document/workflow governance (test_governance_hardening.py) into input-validation robustness: injection resistance in subprocess invocation, provenance-record spoofing resistance, and path-traversal containment. |
| [`operations/tests/tooling/__init__.py`](../operations/tests/tooling/__init__.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_auxiliary_quality_tools.py`](../operations/tests/tooling/test_auxiliary_quality_tools.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_change_scope.py`](../operations/tests/tooling/test_change_scope.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_coverage_policy.py`](../operations/tests/tooling/test_coverage_policy.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_evidence_record.py`](../operations/tests/tooling/test_evidence_record.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_full_traceability.py`](../operations/tests/tooling/test_full_traceability.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_health_check.py`](../operations/tests/tooling/test_health_check.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_links.py`](../operations/tests/tooling/test_links.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_metadata_parsing.py`](../operations/tests/tooling/test_metadata_parsing.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_milestone_lifecycle.py`](../operations/tests/tooling/test_milestone_lifecycle.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_milestone_start_and_task_semantics.py`](../operations/tests/tooling/test_milestone_start_and_task_semantics.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_non_markdown_index.py`](../operations/tests/tooling/test_non_markdown_index.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_project_common.py`](../operations/tests/tooling/test_project_common.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_quality_baseline.py`](../operations/tests/tooling/test_quality_baseline.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_quality_registry.py`](../operations/tests/tooling/test_quality_registry.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_quality_runner.py`](../operations/tests/tooling/test_quality_runner.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_requirement_tooling.py`](../operations/tests/tooling/test_requirement_tooling.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_semantic_consistency.py`](../operations/tests/tooling/test_semantic_consistency.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_task_registry.py`](../operations/tests/tooling/test_task_registry.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_test_catalog.py`](../operations/tests/tooling/test_test_catalog.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_traceability.py`](../operations/tests/tooling/test_traceability.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`operations/tests/tooling/test_versioning.py`](../operations/tests/tooling/test_versioning.py) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`pyproject.toml`](../pyproject.toml) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`src/__init__.py`](../src/__init__.py) | [`TASK_001`](../work/tasks/task_001_arc_001.md) | personal_ai_platform source code. |
| [`src/channels/__init__.py`](../src/channels/__init__.py) | [`TASK_001`](../work/tasks/task_001_arc_001.md) | Channel abstraction layer for multi-interface platform. |
| [`src/channels/base.py`](../src/channels/base.py) | [`TASK_001`](../work/tasks/task_001_arc_001.md) | Base channel abstraction (ARC_CMP_001). |
| [`src/channels/telegram.py`](../src/channels/telegram.py) | [`TASK_001`](../work/tasks/task_001_arc_001.md) | Telegram channel implementation (ARC_CMP_001). |
| [`work/acceptance/.gitkeep`](../work/acceptance/.gitkeep) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`work/acceptance/m01.json`](../work/acceptance/m01.json) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
| [`work/tasks/.gitkeep`](../work/tasks/.gitkeep) | — | _Описание не задано (для этого типа файла нет источника — docstring модуля или заголовочный комментарий скрипта)._ |
