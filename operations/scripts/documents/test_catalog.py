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


# Russian, one-sentence description per test, keyed by "file|method" — written
# from what the test actually verifies (its docstring/name), never invented.
# A test missing here falls back to its own docstring or humanized method
# name (English) below, so a newly added test is never left without a row —
# just without a Russian one until this registry is extended.
RU_DESCRIPTIONS: dict[str, str] = {
    "operations/tests/test_acceptance.py|test_foundation_evidence_targets_machine_path_scope_when_product_scope_is_empty": (
        "Для этапа без объявленного продуктового состава evidence-цели сводятся к области путей автоматики."
    ),
    "operations/tests/test_acceptance.py|test_foundation_profile_passes_only_with_required_evidence_and_context": (
        "Базовый профиль проходит только при наличии всех обязательных доказательств и контекста."
    ),
    "operations/tests/test_acceptance.py|test_invalid_global_coverage_profile_is_rejected": (
        "Некорректный глобальный профиль покрытия отклоняется."
    ),
    "operations/tests/test_acceptance_cli_edges.py|test_main_prepares_transition_and_server_provenance": (
        "CLI готовит переход этапа и фиксирует происхождение серверной проверки."
    ),
    "operations/tests/test_acceptance_cli_edges.py|test_main_rejects_default_branch_and_missing_semantic_review": (
        "CLI отклоняет запуск с default-веткой и без смысловой проверки."
    ),
    "operations/tests/test_acceptance_cli_edges.py|test_evidence_and_semantic_inputs_fail_closed_at_schema_boundary": (
        "Некорректные evidence- и semantic-входы отклоняются на границе схемы."
    ),
    "operations/tests/test_acceptance_cli_edges.py|test_file_digest_is_sha256": (
        "Дайджест файла вычисляется как SHA-256."
    ),
    "operations/tests/test_acceptance_cli_edges.py|test_git_helpers_and_clean_tree_fail_closed": (
        "Git-хелперы и проверка чистого дерева отказывают при любой неопределённости."
    ),
    "operations/tests/test_acceptance_cli_edges.py|test_scope_fallback_and_invalid_canonical_lists": (
        "Резервный scope и некорректные канонические списки обрабатываются корректно."
    ),
    "operations/tests/test_acceptance_cli_edges.py|test_typed_state_helpers_reject_malformed_or_illegal_transitions": (
        "Хелперы типизированных состояний отклоняют некорректные и запрещённые переходы."
    ),
    "operations/tests/test_acceptance_transition.py|test_acceptance_rejects_unfinished_task_before_writing": (
        "Принятие этапа отклоняется, пока есть незавершённая TASK."
    ),
    "operations/tests/test_acceptance_transition.py|test_direct_acceptance_requires_owner_and_sha_bound_dual_evidence": (
        "Прямое принятие требует подтверждения владельца и двух evidence, привязанных к SHA."
    ),
    "operations/tests/test_acceptance_transition.py|test_evidence_bundle_requires_ready_exact_sha_and_full_coverage": (
        "Evidence bundle требует состояния ready, точного SHA и полного покрытия."
    ),
    "operations/tests/test_acceptance_transition.py|test_m01_acceptance_creates_one_record_without_bulk_document_changes": (
        "Принятие m01 создаёт одну запись без массовых правок документов."
    ),
    "operations/tests/test_acceptance_transition.py|test_m01_reaches_semantic_review_without_repository_maintenance_tasks": (
        "m01 доходит до смысловой проверки без служебных TASK по репозиторию."
    ),
    "operations/tests/test_acceptance_transition.py|test_m01_semantic_pass_rejects_unresolved_serious_findings": (
        "Смысловая проверка m01 отклоняется при неразрешённых серьёзных замечаниях."
    ),
    "operations/tests/test_acceptance_transition.py|test_m01_semantic_review_requires_exact_sha_and_full_artifact_scope": (
        "Смысловая проверка m01 требует точного SHA и полного набора артефактов."
    ),
    "operations/tests/test_acceptance_transition.py|test_non_baseline_milestone_also_requires_semantic_review_before_acceptance": (
        "Смысловая проверка обязательна для каждого этапа, а не только для m01."
    ),
    "operations/tests/test_acceptance_transition.py|test_owner_confirmation_must_match_exact_milestone": (
        "Подтверждение владельца должно точно совпадать с идентификатором этапа."
    ),
    "operations/tests/test_acceptance_transition.py|test_semantic_review_schema_applies_to_non_m01_without_v1_scope_fields": (
        "Схема смысловой проверки применяется и к этапам после m01, без полей scope V1."
    ),
    "operations/tests/test_acceptance_transition.py|test_state_transitions_change_only_typed_fields": (
        "Переходы состояний меняют только типизированные поля."
    ),
    "operations/tests/test_boundary_cases.py|test_confirmation_is_case_sensitive": (
        "Подтверждение владельца чувствительно к регистру."
    ),
    "operations/tests/test_boundary_cases.py|test_confirmation_rejects_extra_characters": (
        "Подтверждение отклоняется при лишних символах."
    ),
    "operations/tests/test_boundary_cases.py|test_confirmation_rejects_injection_like_payload": (
        "Подтверждение отклоняет payload, похожий на инъекцию."
    ),
    "operations/tests/test_boundary_cases.py|test_confirmation_rejects_zero_width_injection": (
        "Подтверждение отклоняет символы нулевой ширины."
    ),
    "operations/tests/test_boundary_cases.py|test_confirmation_with_surrounding_whitespace_is_accepted": (
        "Подтверждение с пробелами по краям принимается."
    ),
    "operations/tests/test_boundary_cases.py|test_empty_confirmation_is_rejected": (
        "Пустое подтверждение отклоняется."
    ),
    "operations/tests/test_boundary_cases.py|test_milestone_id_with_unexpected_case_still_produces_lowercase_token": (
        "ID этапа в необычном регистре всё равно даёт токен в нижнем регистре."
    ),
    "operations/tests/test_boundary_cases.py|test_whitespace_only_confirmation_is_rejected": (
        "Подтверждение из одних пробелов отклоняется."
    ),
    "operations/tests/test_boundary_cases.py|test_already_at_target_state_is_idempotent": (
        "Повторный переход в то же состояние идемпотентен."
    ),
    "operations/tests/test_boundary_cases.py|test_crlf_line_endings_are_normalized": (
        "Переносы строк CRLF нормализуются."
    ),
    "operations/tests/test_boundary_cases.py|test_disallowed_transition_raises": (
        "Запрещённый переход состояния вызывает ошибку."
    ),
    "operations/tests/test_boundary_cases.py|test_document_without_front_matter_raises": (
        "Документ без фронтматтера вызывает ошибку."
    ),
    "operations/tests/test_boundary_cases.py|test_empty_body_after_front_matter_is_preserved": (
        "Пустое тело документа после фронтматтера сохраняется как есть."
    ),
    "operations/tests/test_boundary_cases.py|test_empty_document_raises": "Пустой документ вызывает ошибку.",
    "operations/tests/test_boundary_cases.py|test_missing_field_raises": (
        "Отсутствующее обязательное поле вызывает ошибку."
    ),
    "operations/tests/test_boundary_cases.py|test_quoted_field_value_is_normalized": (
        "Значение поля в кавычках нормализуется."
    ),
    "operations/tests/test_boundary_cases.py|test_replace_updated_on_document_without_front_matter_raises": (
        "Замена поля updated в документе без фронтматтера вызывает ошибку."
    ),
    "operations/tests/test_boundary_cases.py|test_unicode_content_in_body_is_preserved": (
        "Unicode-содержимое тела документа сохраняется без искажений."
    ),
    "operations/tests/test_boundary_cases.py|test_unterminated_front_matter_raises": (
        "Незакрытый фронтматтер вызывает ошибку."
    ),
    "operations/tests/test_boundary_cases.py|test_updated_field_missing_raises_when_update_requested": (
        "Запрос обновления при отсутствующем поле updated вызывает ошибку."
    ),
    "operations/tests/test_boundary_cases.py|test_atomic_write_rejects_empty_path_component_gracefully": (
        "Атомарная запись корректно отклоняет пустой компонент пути."
    ),
    "operations/tests/test_boundary_cases.py|test_read_text_on_empty_file": (
        "Чтение текста из пустого файла возвращает пустую строку."
    ),
    "operations/tests/test_boundary_cases.py|test_empty_output_with_failure_code": (
        "Пустой вывод команды при коде ошибки обрабатывается корректно."
    ),
    "operations/tests/test_boundary_cases.py|test_empty_output_with_success_code": (
        "Пустой вывод команды при успешном коде обрабатывается корректно."
    ),
    "operations/tests/test_boundary_cases.py|test_garbage_output_does_not_crash": (
        "Мусорный вывод команды не приводит к падению."
    ),
    "operations/tests/test_boundary_cases.py|test_very_large_output_is_handled": (
        "Очень большой вывод команды обрабатывается корректно."
    ),
    "operations/tests/test_checker_negative_paths.py|test_acceptance_policy_covers_planned_warning_and_missing_links": (
        "Проверка acceptance покрывает planned-предупреждение и отсутствующие ссылки."
    ),
    "operations/tests/test_checker_negative_paths.py|test_authority_graph_rejects_lower_layer_dependency_and_m01_scope": (
        "Граф authority-документов отклоняет зависимость от нижнего слоя и нарушение scope m01."
    ),
    "operations/tests/test_checker_negative_paths.py|test_automation_policy_rejects_bypasses_and_mutating_workflows": (
        "Политика автоматизации отклоняет обходы и изменяющие workflow."
    ),
    "operations/tests/test_checker_negative_paths.py|test_completed_task_rejects_unfilled_auto_generated_result_placeholder": (
        "Завершённая TASK отклоняется при незаполненной автосгенерированной заглушке результата."
    ),
    "operations/tests/test_checker_negative_paths.py|test_completed_task_requires_real_owner_capability_section": (
        "Завершённая TASK требует настоящего раздела «Что это даёт владельцу»."
    ),
    "operations/tests/test_checker_negative_paths.py|test_document_and_requirement_policies_fail_closed": (
        "Политики документов и требований отказывают при любой неопределённости."
    ),
    "operations/tests/test_checker_negative_paths.py|test_metadata_rejects_status_and_duplicate_identifiers": (
        "Метаданные отклоняются при поле status и дублирующихся идентификаторах."
    ),
    "operations/tests/test_checker_negative_paths.py|test_task_policy_reports_conflicting_lifecycle_fields": (
        "Политика TASK сообщает о противоречащих друг другу полях жизненного цикла."
    ),
    "operations/tests/test_checker_negative_paths.py|test_test_spec_policy_rejects_unsafe_and_unlinked_tests": (
        "Политика TEST отклоняет небезопасные и несвязанные тесты."
    ),
    "operations/tests/test_checker_negative_paths.py|test_traceability_rejects_gaps_unknown_edges_and_incomplete_records": (
        "Трассируемость отклоняет пробелы, неизвестные связи и неполные записи."
    ),
    "operations/tests/test_concurrency.py|test_concurrent_writers_never_produce_torn_content": (
        "Множество параллельных потоков записи в один файл никогда не даёт «рваного» содержимого."
    ),
    "operations/tests/test_concurrency.py|test_concurrent_writes_to_distinct_files_all_succeed": (
        "Параллельная запись в разные файлы всегда завершается успешно."
    ),
    "operations/tests/test_concurrency.py|test_readers_never_observe_partial_write_during_concurrent_update": (
        "Читающий поток никогда не видит частично записанный файл при параллельном обновлении."
    ),
    "operations/tests/test_durability.py|test_line_ending_normalization_is_durable_across_rewrites": (
        "Нормализация переносов строк устойчива при повторных перезаписях."
    ),
    "operations/tests/test_durability.py|test_parent_directories_are_created_durably": (
        "Родительские каталоги надёжно создаются при записи."
    ),
    "operations/tests/test_durability.py|test_repeated_identical_writes_are_idempotent_no_op": (
        "Повторная запись идентичного содержимого — идемпотентный no-op."
    ),
    "operations/tests/test_durability.py|test_round_trip_preserves_large_content": (
        "Большой объём содержимого сохраняется без искажений при записи и чтении."
    ),
    "operations/tests/test_durability.py|test_round_trip_preserves_unicode_content": (
        "Unicode-содержимое сохраняется без искажений при записи и чтении."
    ),
    "operations/tests/test_durability.py|test_exception_during_temp_file_write_leaves_original_intact": (
        "Исключение при записи временного файла не повреждает исходный файл."
    ),
    "operations/tests/test_durability.py|test_os_replace_failure_leaves_original_and_no_visible_partial_file": (
        "Сбой os.replace не повреждает исходный файл и не оставляет частичный файл видимым."
    ),
    "operations/tests/test_durability.py|test_gives_up_after_exhausting_retry_attempts": (
        "Запись прекращается после исчерпания всех попыток повтора."
    ),
    "operations/tests/test_durability.py|test_non_permission_os_error_is_not_retried": (
        "Системная ошибка, не связанная с правами доступа, не повторяется."
    ),
    "operations/tests/test_durability.py|test_succeeds_after_transient_permission_errors": (
        "Запись успешна после временных ошибок доступа."
    ),
    "operations/tests/test_generation_safety.py|test_checker_exception_is_localized_and_other_checks_continue": (
        "Исключение в одной проверке не мешает выполнению остальных проверок."
    ),
    "operations/tests/test_generation_safety.py|test_renderer_failure_does_not_partially_write_outputs": (
        "Сбой генератора не оставляет частично записанные производные файлы."
    ),
    "operations/tests/test_governance_hardening.py|test_accepts_and_empty_product_scope_never_produce_empty_evidence_targets": (
        "Accepts-профиль и пустой продуктовый scope никогда не дают пустой набор evidence-целей."
    ),
    "operations/tests/test_governance_hardening.py|test_automation_policy_accepts_additional_read_permission": (
        "Политика автоматизации допускает дополнительное право на чтение."
    ),
    "operations/tests/test_governance_hardening.py|test_automation_policy_accepts_push_trigger_on_main": (
        "Политика автоматизации допускает push-триггер на main."
    ),
    "operations/tests/test_governance_hardening.py|test_automation_policy_rejects_non_read_workflow_permission": (
        "Политика автоматизации отклоняет расширение прав за пределы read одной строкой в permissions."
    ),
    "operations/tests/test_governance_hardening.py|test_automation_policy_rejects_path_filtered_push_trigger": (
        "Отфильтрованный триггер молча перестаёт срабатывать на прямых изменениях main."
    ),
    "operations/tests/test_governance_hardening.py|test_automation_policy_requires_push_trigger_on_main": (
        "Политика автоматизации требует push-триггер на main."
    ),
    "operations/tests/test_governance_hardening.py|test_business_requirements_coverage_accepts_complete_disjoint_split": (
        "Покрытие бизнес-требований принимает полное непересекающееся разбиение по этапам."
    ),
    "operations/tests/test_governance_hardening.py|test_business_requirements_coverage_allows_candidates_after_v1_boundary": (
        "Планирование кандидатов на этапе после V1 разрешено — это прямая задача такого этапа."
    ),
    "operations/tests/test_governance_hardening.py|test_business_requirements_coverage_rejects_core_requirement_deferred_past_v1": (
        "Покрытие бизнес-требований отклоняет core-требование, отложенное за пределы V1."
    ),
    "operations/tests/test_governance_hardening.py|test_business_requirements_coverage_rejects_missing_and_overlapping_br": (
        "Покрытие бизнес-требований отклоняет пропущенные и пересекающиеся BR."
    ),
    "operations/tests/test_governance_hardening.py|test_business_requirements_coverage_rejects_non_core_inside_v1": (
        "Периметр V1 должен точно совпадать с множеством core-требований в обе стороны."
    ),
    "operations/tests/test_governance_hardening.py|test_derived_paths_do_not_block_profile_coverage": (
        "Производные пути не блокируют покрытие профиля."
    ),
    "operations/tests/test_governance_hardening.py|test_document_templates_use_current_russian_structure": (
        "Шаблоны документов используют актуальную русскоязычную структуру."
    ),
    "operations/tests/test_governance_hardening.py|test_dot_directory_path_matches_without_losing_leading_dot": (
        "Путь с каталогом на точку сопоставляется без потери ведущей точки."
    ),
    "operations/tests/test_governance_hardening.py|test_milestone_state_machine_rejects_multiple_active_and_skipped_completion": (
        "Машина состояний этапа отклоняет несколько активных этапов и пропуск завершения."
    ),
    "operations/tests/test_governance_hardening.py|test_publication_and_acceptance_rules_are_consistent": (
        "Правила публикации и принятия этапа согласованы между собой."
    ),
    "operations/tests/test_governance_hardening.py|test_workflow_block_scalar_break_is_detected": (
        "Обнаруживается многострочный блок workflow, закрывающийся молча из-за нулевого отступа."
    ),
    "operations/tests/test_lifecycle_matrix.py|test_m01_accept_m02_start_premature_reject_and_m02_accept": (
        "Полный цикл: принятие m01, старт m02, отказ при преждевременном принятии, затем принятие m02."
    ),
    "operations/tests/test_owner_usability.py|test_capabilities_section_lists_only_completed_tasks_real_capability_text": (
        "Раздел возможностей показывает только завершённые TASK с реальным текстом возможности."
    ),
    "operations/tests/test_owner_usability.py|test_first_unfinished_task_is_selected_by_queue_order": (
        "Первой выбирается незавершённая TASK по порядку очереди."
    ),
    "operations/tests/test_owner_usability.py|test_project_status_is_detailed_without_artificial_percentages": (
        "project_status.md подробен и не содержит искусственных процентов."
    ),
    "operations/tests/test_owner_usability.py|test_project_status_is_the_only_owner_entrypoint": (
        "project_status.md — единственная точка входа для владельца."
    ),
    "operations/tests/test_owner_usability.py|test_project_status_shows_exact_decision_when_owner_is_next": (
        "project_status.md показывает точную команду, когда очередь за владельцем."
    ),
    "operations/tests/test_owner_usability.py|test_repository_maintenance_does_not_remain_in_project_task_queue": (
        "Служебные задачи по репозиторию не остаются в очереди проектных TASK."
    ),
    "operations/tests/test_owner_usability.py|test_technical_status_has_one_russian_owner_action_and_real_foundation_count": (
        "Техническая сводка содержит одно русскоязычное действие владельца и реальное число фундаментальных элементов."
    ),
    "operations/tests/test_owner_usability.py|test_test_specs_keep_owner_steps_safe_and_only_when_manual": (
        "Шаги владельца в TEST безопасны и присутствуют только для ручных проверок."
    ),
    "operations/tests/test_quality_integration.py|test_event_gate_covers_push_pr_and_manual": (
        "Событийный gate покрывает push, PR и ручной запуск."
    ),
    "operations/tests/test_quality_integration.py|test_final_report_matches_current_repository_state": (
        "work/m01_final_report.md полностью соответствует тому, что вычисляет render_final_report()."
    ),
    "operations/tests/test_quality_integration.py|test_only_one_hook_contains_validation_logic": (
        "Логика проверки находится только в одном каноническом хуке."
    ),
    "operations/tests/test_quality_integration.py|test_pre_push_hook_wrapper_delegates_to_canonical_full_profile": (
        "Обёртка pre-push hook делегирует канонический полный профиль проверок."
    ),
    "operations/tests/test_quality_integration.py|test_proposed_technology_adrs_require_m02_evidence": (
        "Предложенные технологические ADR требуют evidence по m02."
    ),
    "operations/tests/test_quality_integration.py|test_quality_record_requires_exact_sha_and_present_artifacts": (
        "Запись о прогоне качества требует точного SHA и реально существующих артефактов."
    ),
    "operations/tests/test_quality_integration.py|test_shellcheck_covers_both_pre_commit_and_pre_push_hooks": (
        "ShellCheck проверяет и pre-commit, и pre-push хуки."
    ),
    "operations/tests/test_scope_coverage.py|test_foundation_paths_replace_empty_product_scope_in_status_counts": (
        "Пути фундамента заменяют пустой продуктовый scope в счётчиках статуса."
    ),
    "operations/tests/test_scope_coverage.py|test_global_evidence_covers_scope_only_when_passed": (
        "Глобальное evidence покрывает scope только когда проверка прошла."
    ),
    "operations/tests/test_scope_coverage.py|test_m01_scope_uses_entire_tracked_tree_not_only_last_commit": (
        "Scope m01 берёт всё отслеживаемое дерево файлов, а не только последний коммит."
    ),
    "operations/tests/test_scope_coverage.py|test_task_test_mode_blocks_uncovered_scope_and_task_implements": (
        "Режим TASK/TEST блокирует непокрытый scope и незаполненный implements."
    ),
    "operations/tests/test_security_extended.py|test_relative_posix_refuses_dotdot_escape": (
        "relative_posix отказывает в выходе за пределы через «..»."
    ),
    "operations/tests/test_security_extended.py|test_relative_posix_refuses_sibling_directory": (
        "relative_posix отказывает в переходе в соседний каталог."
    ),
    "operations/tests/test_security_extended.py|test_http_instead_of_https_is_rejected": (
        "Ссылка по http вместо https отклоняется."
    ),
    "operations/tests/test_security_extended.py|test_lookalike_domain_is_rejected": (
        "Домен, похожий на настоящий (lookalike), отклоняется."
    ),
    "operations/tests/test_security_extended.py|test_mismatched_expected_sha_is_rejected": (
        "Несовпадение ожидаемого SHA отклоняется."
    ),
    "operations/tests/test_security_extended.py|test_missing_fields_are_reported_not_silently_accepted": (
        "Отсутствующие поля сообщаются явно, а не принимаются молча."
    ),
    "operations/tests/test_security_extended.py|test_non_dict_input_is_rejected": (
        "Вход, не являющийся словарём, отклоняется."
    ),
    "operations/tests/test_security_extended.py|test_non_hex_sha_is_rejected": "SHA не в hex-формате отклоняется.",
    "operations/tests/test_security_extended.py|test_non_numeric_run_id_is_rejected": (
        "Нечисловой run_id отклоняется."
    ),
    "operations/tests/test_security_extended.py|test_path_traversal_in_run_url_is_rejected": (
        "Обход пути в run_url отклоняется."
    ),
    "operations/tests/test_security_extended.py|test_sha_with_injected_whitespace_is_rejected": (
        "SHA с внедрёнными пробелами отклоняется."
    ),
    "operations/tests/test_security_extended.py|test_short_sha_is_rejected": "Слишком короткий SHA отклоняется.",
    "operations/tests/test_security_extended.py|test_valid_source_passes": "Корректный источник проходит проверку.",
    "operations/tests/test_security_extended.py|test_command_substitution_syntax_is_inert": (
        "Синтаксис подстановки команд обезврежен и не выполняется."
    ),
    "operations/tests/test_security_extended.py|test_nonexistent_binary_fails_closed_not_open": (
        "Несуществующий исполняемый файл приводит к отказу, а не к молчаливому пропуску."
    ),
    "operations/tests/test_security_extended.py|test_shell_metacharacters_in_argument_are_treated_literally": (
        "Спецсимволы shell в аргументе обрабатываются как обычный текст."
    ),
    "operations/tests/tooling/test_auxiliary_quality_tools.py|test_component_parser_and_document_are_deterministic": (
        "Разбор компонента и генерация документа детерминированы."
    ),
    "operations/tests/tooling/test_auxiliary_quality_tools.py|test_generates_only_in_scope_uncovered_components": (
        "Автогенерация создаёт TASK только для непокрытых компонентов в рамках scope."
    ),
    "operations/tests/tooling/test_auxiliary_quality_tools.py|test_generation_is_blocked_before_an_active_scoped_stage": (
        "Автогенерация блокируется до наступления активного этапа с заданным scope."
    ),
    "operations/tests/tooling/test_auxiliary_quality_tools.py|test_generate_bundle_main_handles_missing_and_successful_inputs": (
        "CLI сборки evidence bundle обрабатывает и отсутствующие, и успешные входные данные."
    ),
    "operations/tests/tooling/test_auxiliary_quality_tools.py|test_pr_comment_formats_failures_and_main_writes_utf8": (
        "Комментарий к PR форматирует ошибки, CLI записывает его в UTF-8."
    ),
    "operations/tests/tooling/test_auxiliary_quality_tools.py|test_quality_record_main_rejects_invalid_sha_and_writes_valid_record": (
        "CLI записи качества отклоняет некорректный SHA и записывает валидную запись."
    ),
    "operations/tests/tooling/test_auxiliary_quality_tools.py|test_owner_action_practicality_reports_each_policy_violation": (
        "Проверка практичности действия владельца сообщает о каждом нарушении."
    ),
    "operations/tests/tooling/test_auxiliary_quality_tools.py|test_planned_milestone_defers_test_coverage_gate": (
        "Для планируемого этапа gate покрытия тестами откладывается."
    ),
    "operations/tests/tooling/test_auxiliary_quality_tools.py|test_requirement_coverage_detects_uncovered_and_empty_tests": (
        "Проверка покрытия требований находит непокрытые и пустые TEST."
    ),
    "operations/tests/tooling/test_auxiliary_quality_tools.py|test_task_path_validation_reports_missing_exact_and_glob_paths": (
        "Проверка путей TASK сообщает об отсутствующих точных путях и масках."
    ),
    "operations/tests/tooling/test_auxiliary_quality_tools.py|test_technical_status_writes_snapshot_bound_to_commit": (
        "Техническая сводка записывает снимок, привязанный к коммиту."
    ),
    "operations/tests/tooling/test_auxiliary_quality_tools.py|test_auto_link_finds_architecture_implementation": (
        "Автосвязывание находит реализацию архитектурного компонента."
    ),
    "operations/tests/tooling/test_auxiliary_quality_tools.py|test_yaml_helpers_preserve_front_matter": (
        "YAML-хелперы сохраняют фронтматтер без искажений."
    ),
    "operations/tests/tooling/test_change_scope.py|test_active_task_covers_only_declared_paths": (
        "Активная TASK покрывает только заявленные в allowed_paths пути."
    ),
    "operations/tests/tooling/test_change_scope.py|test_completed_task_is_eligible_only_when_its_card_changes": (
        "Завершённая TASK учитывается только если менялась её собственная карточка."
    ),
    "operations/tests/tooling/test_change_scope.py|test_foundation_milestone_does_not_require_task_for_specifications": (
        "Пока активный этап не объявляет продуктовый состав, поставки продукта нет."
    ),
    "operations/tests/tooling/test_change_scope.py|test_repository_maintenance_does_not_require_project_task": (
        "Служебное изменение репозитория не требует проектной TASK."
    ),
    "operations/tests/tooling/test_change_scope.py|test_current_branch_is_honest": (
        "Определение текущей ветки честно отражает реальное состояние git."
    ),
    "operations/tests/tooling/test_change_scope.py|test_metadata_validation_runs_without_hardcoded_commits": (
        "Валидация метаданных работает по доступной истории git, без зашитых в код коммитов."
    ),
    "operations/tests/tooling/test_coverage_policy.py|test_changed_lines_fails_closed_when_git_diff_fails": (
        "Определение изменённых строк отказывает при сбое git diff."
    ),
    "operations/tests/tooling/test_coverage_policy.py|test_evaluate_fails_missing_schema_modules_and_uncovered_diff": (
        "Оценка покрытия падает при отсутствующих в схеме модулях и непокрытом diff."
    ),
    "operations/tests/tooling/test_coverage_policy.py|test_evaluate_passes_aggregate_module_and_diff_thresholds": (
        "Оценка покрытия проходит при соблюдении общего, модульного и diff-порогов."
    ),
    "operations/tests/tooling/test_coverage_policy.py|test_load_policy_and_main_success_and_failure_paths": (
        "Загрузка политики покрытия и CLI обрабатывают успешный и провальный сценарии."
    ),
    "operations/tests/tooling/test_coverage_policy.py|test_parse_changed_lines_handles_new_modified_empty_and_deleted_hunks": (
        "Разбор изменённых строк обрабатывает новые, изменённые, пустые и удалённые hunk'и."
    ),
    "operations/tests/tooling/test_evidence_record.py|test_build_bundle_normalizes_evidence_and_tests": (
        "Сборка evidence bundle нормализует evidence и тесты."
    ),
    "operations/tests/tooling/test_evidence_record.py|test_targets_merge_tests_profiles_and_fallback_paths": (
        "Evidence-цели объединяют тесты, профили и резервные пути."
    ),
    "operations/tests/tooling/test_evidence_record.py|test_write_bundle_uses_sha_name_and_atomic_latest": (
        "Запись evidence bundle использует имя по SHA и атомарно обновляет latest."
    ),
    "operations/tests/tooling/test_full_traceability.py|test_core_requirement_without_system_decomposition_is_rejected": (
        "Core-требование без декомпозиции на системные требования отклоняется."
    ),
    "operations/tests/tooling/test_full_traceability.py|test_missing_decomposition_architecture_infrastructure_and_evidence_are_rejected": (
        "Отсутствующая декомпозиция на архитектуру, инфраструктуру и evidence отклоняется."
    ),
    "operations/tests/tooling/test_full_traceability.py|test_repository_has_complete_v1_chains_and_test_evidence": (
        "В репозитории есть полные цепочки трассировки V1 и evidence по тестам."
    ),
    "operations/tests/tooling/test_health_check.py|test_healthy_when_everything_clean": (
        "Репозиторий считается здоровым, когда всё чисто."
    ),
    "operations/tests/tooling/test_health_check.py|test_needs_attention_when_tests_fail": (
        "Репозиторий требует внимания при падающих тестах."
    ),
    "operations/tests/tooling/test_health_check.py|test_needs_attention_when_working_tree_dirty": (
        "Репозиторий требует внимания при незакоммиченных изменениях."
    ),
    "operations/tests/tooling/test_health_check.py|test_counts_ruff_issues_from_summary_line_and_flags_noncompliant_formatting": (
        "Подсчёт замечаний ruff по итоговой строке и флаг несоответствия форматированию."
    ),
    "operations/tests/tooling/test_health_check.py|test_missing_tools_leave_safe_defaults": (
        "Отсутствующие инструменты дают безопасные значения по умолчанию."
    ),
    "operations/tests/tooling/test_health_check.py|test_ruff_output_with_no_findings_counts_zero": (
        "Вывод ruff без замечаний даёт ноль в счётчике."
    ),
    "operations/tests/tooling/test_health_check.py|test_dirty_working_tree_is_reported_as_not_clean": (
        "Незакоммиченное рабочее дерево отмечается как «не чистое»."
    ),
    "operations/tests/tooling/test_health_check.py|test_reports_real_commit_and_branch_metadata": (
        "Отчёт содержит реальные метаданные коммита и ветки."
    ),
    "operations/tests/tooling/test_health_check.py|test_parses_pytest_summary_line": (
        "Итоговая строка pytest корректно разбирается."
    ),
    "operations/tests/tooling/test_health_check.py|test_reads_coverage_percent_from_runtime_coverage_json": (
        "Процент покрытия читается из runtime/coverage.json."
    ),
    "operations/tests/tooling/test_health_check.py|test_generate_report_includes_key_metrics": (
        "Сгенерированный отчёт включает ключевые метрики."
    ),
    "operations/tests/tooling/test_health_check.py|test_print_summary_writes_key_lines_to_stdout": (
        "Краткая сводка выводит ключевые строки в stdout."
    ),
    "operations/tests/tooling/test_links.py|test_accepts_clickable_markdown_reference": (
        "Кликабельная markdown-ссылка принимается."
    ),
    "operations/tests/tooling/test_links.py|test_accepts_internal_anchor_without_repeating_filename": (
        "Внутренний якорь без повтора имени файла принимается."
    ),
    "operations/tests/tooling/test_links.py|test_ignores_code_blocks_and_future_filename_examples": (
        "Проверка ссылок игнорирует блоки кода и примеры будущих имён файлов."
    ),
    "operations/tests/tooling/test_links.py|test_rejects_link_from_document_to_itself": (
        "Ссылка документа на самого себя отклоняется."
    ),
    "operations/tests/tooling/test_links.py|test_rejects_unlinked_existing_markdown_reference": (
        "Упоминание существующего документа без ссылки отклоняется."
    ),
    "operations/tests/tooling/test_links.py|test_runtime_artifact_does_not_change_document_check": (
        "Артефакты в runtime/ не влияют на результат проверки документов."
    ),
    "operations/tests/tooling/test_markdown_index.py|test_generated_directory_is_excluded": (
        "Каталог generated/ исключён из индекса."
    ),
    "operations/tests/tooling/test_markdown_index.py|test_lists_every_tracked_markdown_file_exactly_once": (
        "Каждый отслеживаемый .md файл перечислен в индексе ровно один раз."
    ),
    "operations/tests/tooling/test_markdown_index.py|test_no_longer_filters_by_primary_document_status": (
        "Индекс больше не фильтруется по признаку «первичности» документа."
    ),
    "operations/tests/tooling/test_markdown_index.py|test_starts_with_generated_marker_and_frontmatter": (
        "Файл начинается с generated-маркера и фронтматтера."
    ),
    "operations/tests/tooling/test_metadata_parsing.py|test_duplicate_key_is_rejected_instead_of_silently_overwritten": (
        "Дублирующийся ключ фронтматтера отклоняется, а не молча перезаписывается."
    ),
    "operations/tests/tooling/test_metadata_parsing.py|test_duplicate_list_key_is_rejected": (
        "Дублирующийся ключ списка отклоняется."
    ),
    "operations/tests/tooling/test_metadata_parsing.py|test_empty_inline_list_still_parses": (
        "Пустой инлайн-список всё равно успешно разбирается."
    ),
    "operations/tests/tooling/test_metadata_parsing.py|test_inline_list_splits_on_top_level_commas_only": (
        "Инлайн-список разбивается только по запятым верхнего уровня."
    ),
    "operations/tests/tooling/test_metadata_parsing.py|test_inline_list_with_unclosed_quote_is_rejected": (
        "Инлайн-список с незакрытой кавычкой отклоняется."
    ),
    "operations/tests/tooling/test_milestone_lifecycle.py|test_creates_only_final_report": (
        "При старте этапа создаётся только final_report.md; owner_checklist.md и semantic_review.md — по решению, не автоматически."
    ),
    "operations/tests/tooling/test_milestone_lifecycle.py|test_does_not_overwrite_existing_files": (
        "Инициализация не перезаписывает уже существующие файлы."
    ),
    "operations/tests/tooling/test_milestone_lifecycle.py|test_fails_when_milestone_missing_from_milestones_md": (
        "Инициализация падает, если этап отсутствует в milestones.md."
    ),
    "operations/tests/tooling/test_milestone_lifecycle.py|test_final_report_frontmatter_references_milestone": (
        "Фронтматтер финального отчёта ссылается на свой этап."
    ),
    "operations/tests/tooling/test_milestone_lifecycle.py|test_final_report_starts_pending": (
        "Финальный отчёт при создании начинается в состоянии pending."
    ),
    "operations/tests/tooling/test_milestone_lifecycle.py|test_marks_report_completed_at_the_completion_commit": (
        "Отчёт помечается завершённым именно на коммите принятия этапа."
    ),
    "operations/tests/tooling/test_milestone_lifecycle.py|test_refuses_to_render_when_completion_commit_is_a_shallow_boundary": (
        "Рендер отказывает, если коммит принятия — граница shallow-клона (история недостоверна)."
    ),
    "operations/tests/tooling/test_milestone_lifecycle.py|test_render_pending_milestone_stays_in_progress": (
        "Рендер незавершённого этапа сохраняет состояние in-progress."
    ),
    "operations/tests/tooling/test_milestone_lifecycle.py|test_returns_false_when_milestone_unknown": (
        "Возвращает false, если final_report.md есть на диске, а в milestones.md для него нет записи."
    ),
    "operations/tests/tooling/test_milestone_lifecycle.py|test_returns_false_when_report_missing": (
        "Возвращает false, если отчёт отсутствует на диске."
    ),
    "operations/tests/tooling/test_milestone_start_and_task_semantics.py|test_apply_is_atomic_after_preflight_and_updates_metadata": (
        "Применение перехода атомарно после preflight и обновляет метаданные."
    ),
    "operations/tests/tooling/test_milestone_start_and_task_semantics.py|test_cli_reports_dry_run_apply_and_blockers": (
        "CLI сообщает о dry-run, применении и блокерах."
    ),
    "operations/tests/tooling/test_milestone_start_and_task_semantics.py|test_delivery_closure_ignores_unknown_identifiers": (
        "Замыкание поставки игнорирует неизвестные идентификаторы."
    ),
    "operations/tests/tooling/test_milestone_start_and_task_semantics.py|test_preflight_and_transition_report_each_atomic_start_blocker": (
        "Preflight и переход сообщают о каждом блокере атомарного старта."
    ),
    "operations/tests/tooling/test_milestone_start_and_task_semantics.py|test_semantic_closure_and_valid_preflight_cover_transitive_business_scope": (
        "Смысловое замыкание и валидный preflight покрывают транзитивный бизнес-scope."
    ),
    "operations/tests/tooling/test_milestone_start_and_task_semantics.py|test_unrelated_component_claim_and_missing_test_fail_closed": (
        "Заявка на несвязанный компонент и отсутствующий TEST отклоняются."
    ),
    "operations/tests/tooling/test_non_markdown_index.py|test_descriptions_are_russian_and_simple": (
        "Описания в индексе — на русском языке и просто сформулированы."
    ),
    "operations/tests/tooling/test_non_markdown_index.py|test_distinct_python_modules_get_their_own_real_description": (
        "Разные Python-модули получают собственное настоящее описание."
    ),
    "operations/tests/tooling/test_non_markdown_index.py|test_does_not_list_any_markdown_document": (
        "Markdown-документы не попадают в этот индекс."
    ),
    "operations/tests/tooling/test_non_markdown_index.py|test_empty_init_file_gets_the_honest_package_marker": (
        "Пустой __init__.py получает честную пометку файла-маркера пакета."
    ),
    "operations/tests/tooling/test_non_markdown_index.py|test_file_with_no_owning_task_shows_no_link": (
        "Файл без владеющей TASK показывает прочерк вместо ссылки."
    ),
    "operations/tests/tooling/test_non_markdown_index.py|test_file_with_no_registered_description_falls_back_to_dash": (
        "Файл без записи в реестре описаний получает прочерк."
    ),
    "operations/tests/tooling/test_non_markdown_index.py|test_lists_every_tracked_non_markdown_file_exactly_once": (
        "Каждый отслеживаемый не-.md файл перечислен ровно один раз."
    ),
    "operations/tests/tooling/test_non_markdown_index.py|test_shell_script_description_is_russian": (
        "Описание shell-скрипта — на русском языке."
    ),
    "operations/tests/tooling/test_non_markdown_index.py|test_starts_with_generated_marker_and_frontmatter": (
        "Файл начинается с generated-маркера и фронтматтера."
    ),
    "operations/tests/tooling/test_non_markdown_index.py|test_task_001_deliverables_link_to_their_task": (
        "Файлы, поставленные TASK_001, ссылаются на свою задачу."
    ),
    "operations/tests/tooling/test_project_common.py|test_repository_with_a_commit_reports_full_sha": (
        "Репозиторий с коммитом возвращает полный SHA."
    ),
    "operations/tests/tooling/test_project_common.py|test_repository_with_no_commits_reports_none_not_head": (
        "Репозиторий без коммитов возвращает None, а не HEAD."
    ),
    "operations/tests/tooling/test_project_common.py|test_invalid_utf8_raises_with_path_in_message": (
        "Некорректный UTF-8 вызывает ошибку с путём файла в тексте."
    ),
    "operations/tests/tooling/test_quality_baseline.py|test_allows_existing_debt_at_or_below_budget": (
        "Существующий долг в пределах бюджета допускается."
    ),
    "operations/tests/tooling/test_quality_baseline.py|test_blocks_error_count_increase": (
        "Рост числа ошибок mypy блокируется."
    ),
    "operations/tests/tooling/test_quality_baseline.py|test_blocks_new_error_code_even_when_total_is_unchanged": (
        "Новый код ошибки блокируется, даже если общее число не выросло."
    ),
    "operations/tests/tooling/test_quality_baseline.py|test_blocks_tool_failure_without_countable_errors": (
        "Сбой инструмента без исчисляемых ошибок блокируется."
    ),
    "operations/tests/tooling/test_quality_registry.py|test_evidence_sources_cover_checker_named_checks_and_records": (
        "Источники evidence покрывают именованные проверки checker'а и записи."
    ),
    "operations/tests/tooling/test_quality_registry.py|test_invalid_registry_reports_every_schema_boundary": (
        "Некорректный реестр сообщает о каждом нарушении схемы."
    ),
    "operations/tests/tooling/test_quality_registry.py|test_manual_record_changes_missing_to_passed": (
        "Ручная запись переводит статус из missing в passed."
    ),
    "operations/tests/tooling/test_quality_registry.py|test_profile_selection_and_impact_ignore_malformed_rows": (
        "Выбор профиля и оценка влияния игнорируют некорректные строки."
    ),
    "operations/tests/tooling/test_quality_registry.py|test_repository_registry_defines_only_current_quality_horizon": (
        "Реестр репозитория описывает только текущий горизонт качества."
    ),
    "operations/tests/tooling/test_quality_registry.py|test_server_evidence_schema_rejects_forgery_stale_sha_and_bad_artifacts": (
        "Схема серверного evidence отклоняет подделку, устаревший SHA и некорректные артефакты."
    ),
    "operations/tests/tooling/test_quality_runner.py|test_canonical_unittest_runner_rejects_skips": (
        "Канонический раннер тестов отклоняет пропущенные (skipped) тесты."
    ),
    "operations/tests/tooling/test_quality_runner.py|test_configuration_and_permission_checks_fail_closed": (
        "Проверки конфигурации и прав доступа отказывают при любой неопределённости."
    ),
    "operations/tests/tooling/test_quality_runner.py|test_fast_and_full_profiles_use_canonical_nonduplicated_steps": (
        "Профили fast и full используют канонические шаги без дублирования."
    ),
    "operations/tests/tooling/test_quality_runner.py|test_main_routes_profiles_and_reports_failures": (
        "CLI раннера выбирает профиль и сообщает об ошибках."
    ),
    "operations/tests/tooling/test_quality_runner.py|test_run_step_records_combined_output_and_propagates_failure": (
        "Шаг прогона записывает совмещённый вывод и пробрасывает ошибку."
    ),
    "operations/tests/tooling/test_quality_runner.py|test_run_step_writes_placeholder_for_empty_but_successful_output": (
        "Чистый прогон инструмента (например, Vulture без находок) даёт пустой вывод, для которого пишется заглушка."
    ),
    "operations/tests/tooling/test_requirement_tooling.py|test_apply_wizard_result_reports_the_complete_operation": (
        "Применение результата wizard сообщает о полностью завершённой операции."
    ),
    "operations/tests/tooling/test_requirement_tooling.py|test_apply_writes_specifications_tests_tasks_and_milestone": (
        "Применение результата wizard записывает спецификации, TEST, TASK и этап."
    ),
    "operations/tests/tooling/test_requirement_tooling.py|test_missing_optional_specifications_are_not_reported": (
        "Отсутствующие необязательные спецификации не считаются ошибкой."
    ),
    "operations/tests/tooling/test_requirement_tooling.py|test_number_and_yaml_helpers": (
        "Числовые и YAML-хелперы wizard'а работают корректно."
    ),
    "operations/tests/tooling/test_requirement_tooling.py|test_collect_requirement_info_normalizes_defaults": (
        "Сбор информации о требовании нормализует значения по умолчанию."
    ),
    "operations/tests/tooling/test_requirement_tooling.py|test_context_uses_an_independent_acceptance_criteria_list": (
        "Контекст использует независимый список критериев приёмки."
    ),
    "operations/tests/tooling/test_requirement_tooling.py|test_generators_create_complete_related_artifacts": (
        "Генераторы создают полный набор связанных артефактов."
    ),
    "operations/tests/tooling/test_requirement_tooling.py|test_interactive_wizard_builds_summary": (
        "Интерактивный wizard формирует итоговую сводку."
    ),
    "operations/tests/tooling/test_requirement_tooling.py|test_collect_stage_info_accepts_indices_names_and_defaults": (
        "Сбор информации об этапе принимает индексы, имена и значения по умолчанию."
    ),
    "operations/tests/tooling/test_requirement_tooling.py|test_get_next_stage_handles_current_and_invalid_ids": (
        "Определение следующего этапа обрабатывает текущий и некорректные ID."
    ),
    "operations/tests/tooling/test_requirement_tooling.py|test_stage_plan_and_interactive_report": (
        "План этапа и интерактивный отчёт формируются корректно."
    ),
    "operations/tests/tooling/test_semantic_consistency.py|test_adr_target_from_another_stage_is_rejected": (
        "Ссылка ADR на решение с другого этапа отклоняется."
    ),
    "operations/tests/tooling/test_semantic_consistency.py|test_implicit_system_dependency_is_rejected": (
        "Неявная системная зависимость отклоняется."
    ),
    "operations/tests/tooling/test_semantic_consistency.py|test_repository_semantics_are_consistent": (
        "Смысловые связи в репозитории непротиворечивы."
    ),
    "operations/tests/tooling/test_task_registry.py|test_completed_tasks_must_form_queue_prefix": (
        "Завершённые TASK должны образовывать непрерывный префикс очереди."
    ),
    "operations/tests/tooling/test_task_registry.py|test_duplicate_task_id_is_rejected_before_rendering": (
        "Дублирующийся ID TASK отклоняется до рендеринга."
    ),
    "operations/tests/tooling/test_task_registry.py|test_each_task_depends_on_immediate_predecessor": (
        "Каждая TASK зависит от непосредственно предыдущей."
    ),
    "operations/tests/tooling/test_task_registry.py|test_only_one_task_can_be_active": "Активной может быть только одна TASK.",
    "operations/tests/tooling/test_task_registry.py|test_task_ids_must_be_continuous": (
        "ID задач TASK должны идти без пропусков."
    ),
    "operations/tests/tooling/test_task_registry.py|test_test_traces_to_task_and_task_implements_requirements": (
        "TEST ссылается на TASK, а TASK реализует требования."
    ),
    "operations/tests/tooling/test_task_registry.py|test_task_id_pattern_accepts_three_digits_and_rejects_four": (
        "Формат ID TASK принимает три цифры и отклоняет четыре."
    ),
    "operations/tests/tooling/test_task_registry.py|test_test_id_pattern_accepts_three_digits_and_rejects_four": (
        "Формат ID TEST принимает три цифры и отклоняет четыре."
    ),
    "operations/tests/tooling/test_test_catalog.py|test_category_is_always_a_known_label": (
        "Категория теста всегда одна из известных меток."
    ),
    "operations/tests/tooling/test_test_catalog.py|test_discovers_every_test_the_canonical_runner_would_run": (
        "Каталог находит ровно те тесты, что запускает канонический раннер."
    ),
    "operations/tests/tooling/test_test_catalog.py|test_each_row_has_a_non_empty_description": (
        "У каждой строки каталога непустое описание."
    ),
    "operations/tests/tooling/test_test_catalog.py|test_every_row_appears_in_rendered_table": (
        "Каждая собранная строка присутствует в отрендеренной таблице."
    ),
    "operations/tests/tooling/test_test_catalog.py|test_output_has_generated_header_and_frontmatter": (
        "Файл начинается с generated-маркера и фронтматтера."
    ),
    "operations/tests/tooling/test_test_catalog.py|test_rendering_is_idempotent": "Повторный рендер даёт идентичный результат.",
    "operations/tests/tooling/test_test_catalog.py|test_total_count_matches_collected_rows": (
        "Итоговое число тестов совпадает с числом собранных строк."
    ),
    "operations/tests/tooling/test_traceability.py|test_duplicate_traceable_id_is_rejected": (
        "Дублирующийся трассируемый ID отклоняется."
    ),
    "operations/tests/tooling/test_traceability.py|test_lower_layers_never_duplicate_the_threat_to_control_edge": (
        "Связь «угроза — мера» хранится один раз, как THR.mitigated_by."
    ),
    "operations/tests/tooling/test_traceability.py|test_milestone_scope_uses_only_composition_line_and_expands_ranges": (
        "Scope этапа берётся только из строки состава и разворачивает диапазоны."
    ),
    "operations/tests/tooling/test_traceability.py|test_repository_contains_all_traceable_families_and_relations": (
        "В репозитории присутствуют все семейства трассируемых элементов и их связи."
    ),
    "operations/tests/tooling/test_traceability.py|test_repository_milestone_composition_is_not_silently_empty": (
        "Состав этапа в репозитории не бывает молча пустым."
    ),
    "operations/tests/tooling/test_traceability.py|test_threat_reference_from_lower_layer_is_rejected": (
        "Ссылка на угрозу с нижнего слоя отклоняется."
    ),
    "operations/tests/tooling/test_versioning.py|test_increments_minor_version": "Минорная версия увеличивается на единицу.",
    "operations/tests/tooling/test_versioning.py|test_returns_input_unchanged_when_not_semantic_version": (
        "Не-semver значение возвращается без изменений."
    ),
    "operations/tests/tooling/test_versioning.py|test_rolls_over_to_next_major_at_minor_nine": (
        "После минорной версии 9 версия переходит на следующую мажорную."
    ),
    "operations/tests/tooling/test_versioning.py|test_bumps_version_field_in_frontmatter": (
        "Поле version во фронтматтере повышается."
    ),
    "operations/tests/tooling/test_versioning.py|test_preserves_rest_of_document_content": (
        "Остальное содержимое документа сохраняется без изменений."
    ),
    "operations/tests/tooling/test_versioning.py|test_returns_false_for_non_markdown_file": (
        "Для не-Markdown файла возвращается false."
    ),
    "operations/tests/tooling/test_versioning.py|test_returns_false_when_file_missing": (
        "Возвращает false, если файл отсутствует."
    ),
    "operations/tests/tooling/test_versioning.py|test_returns_false_when_no_version_field_present": (
        "Возвращает false, если поле version отсутствует."
    ),
    "operations/tests/tooling/test_versioning.py|test_skips_fully_generated_files": (
        "Полностью автогенерируемые файлы пропускаются."
    ),
    "operations/tests/integration/test_quality_pipeline.py|test_bandit_runs_without_errors": (
        "Bandit (сканер безопасности) запускается без ошибок."
    ),
    "operations/tests/integration/test_quality_pipeline.py|test_code_analyzer_finds_issues_or_clean": (
        "code_analyzer.py работает без исключений и корректно находит проблемы (или их отсутствие)."
    ),
    "operations/tests/integration/test_quality_pipeline.py|test_code_analyzer_produces_valid_json": (
        "code_analyzer.py выдаёт корректный JSON."
    ),
    "operations/tests/integration/test_quality_pipeline.py|test_mypy_type_checking_integration": (
        "Проверка типов mypy с baseline работает корректно."
    ),
    "operations/tests/integration/test_quality_pipeline.py|test_ruff_integration": (
        "Ruff-линтер работает с конфигурацией проекта."
    ),
    "operations/tests/integration/test_quality_pipeline.py|test_vulture_runs_without_errors": (
        "Vulture (поиск мёртвого кода) запускается без ошибок на этом же коде."
    ),
    "operations/tests/performance/test_critical_paths.py|test_atomic_write_no_op_is_fast": (
        "Повторная запись идентичного содержимого быстро завершается через путь чтения-сравнения."
    ),
    "operations/tests/performance/test_critical_paths.py|test_atomic_write_scales_linearly_with_file_count": (
        "Время атомарной записи растёт линейно от числа файлов."
    ),
    "operations/tests/performance/test_critical_paths.py|test_snake_case_check_handles_many_calls_quickly": (
        "Проверка snake_case быстро обрабатывает большое число вызовов."
    ),
    "operations/tests/performance/test_critical_paths.py|test_read_text_scales_with_size": (
        "Время чтения текста растёт линейно от размера файла."
    ),
    "operations/tests/stress/test_scalability.py|test_deep_and_wide_tree_traversal_is_fast": (
        "Обход глубокого и широкого дерева файлов выполняется быстро."
    ),
    "operations/tests/stress/test_scalability.py|test_maximum_supported_milestone_count_parses_correctly": (
        "Максимально поддерживаемое число этапов корректно разбирается."
    ),
    "operations/tests/stress/test_scalability.py|test_scaling_from_10_to_90_milestones_stays_roughly_linear": (
        "Рост от 10 до 90 этапов остаётся примерно линейным по времени."
    ),
    "operations/tests/stress/test_scalability.py|test_large_chain_with_single_broken_link_is_detected": (
        "Большая цепочка с одной разорванной связью обнаруживается."
    ),
    "operations/tests/stress/test_scalability.py|test_large_valid_chain_validates_without_error": (
        "Большая корректная цепочка проходит валидацию без ошибок."
    ),
    "operations/tests/stress/test_scalability.py|test_multiple_active_tasks_detected_even_at_scale": (
        "Несколько активных TASK обнаруживаются даже при большом объёме данных."
    ),
    "operations/tests/product/test_channels.py|test_each_message_gets_a_unique_task_id": (
        "Каждое сообщение получает уникальный ID задачи."
    ),
    "operations/tests/product/test_channels.py|test_mark_cancelled_sets_state_and_timestamp": (
        "Отметка «отменено» устанавливает статус и время."
    ),
    "operations/tests/product/test_channels.py|test_mark_completed_sets_state_and_timestamp": (
        "Отметка «завершено» устанавливает статус и время."
    ),
    "operations/tests/product/test_channels.py|test_mark_failed_records_error_message": (
        "Отметка «ошибка» сохраняет текст ошибки."
    ),
    "operations/tests/product/test_channels.py|test_mark_running_sets_running_state": (
        "Отметка «выполняется» устанавливает соответствующий статус."
    ),
    "operations/tests/product/test_channels.py|test_starts_pending": "Задача изначально создаётся в статусе «ожидает».",
    "operations/tests/product/test_channels.py|test_get_response_is_none_before_send": (
        "Ответ равен None до отправки."
    ),
    "operations/tests/product/test_channels.py|test_inject_and_receive_round_trips_message": (
        "Внедрённое сообщение корректно доходит через приём."
    ),
    "operations/tests/product/test_channels.py|test_messages_are_received_in_fifo_order": (
        "Сообщения принимаются в порядке очереди (FIFO)."
    ),
    "operations/tests/product/test_channels.py|test_receive_without_token_raises_channel_error": (
        "Приём без токена вызывает ChannelError."
    ),
    "operations/tests/product/test_channels.py|test_reset_clears_responses_and_queue": (
        "Сброс очищает ответы и очередь."
    ),
    "operations/tests/product/test_channels.py|test_send_status_formats_state_into_response": (
        "Отправка статуса форматирует состояние в ответ."
    ),
    "operations/tests/product/test_channels.py|test_send_stores_response_for_task": (
        "Отправка сохраняет ответ для задачи."
    ),
    "operations/tests/product/test_channels.py|test_send_without_token_raises_channel_error": (
        "Отправка без токена вызывает ChannelError."
    ),
    "operations/tests/product/test_channels.py|test_channel_type_is_telegram": "Тип канала — Telegram.",
    "operations/tests/product/test_channels.py|test_default_token_is_empty": "Токен по умолчанию пуст.",
}


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
        file = f"{start_dir}/{module_dotted.replace('.', '/')}.py"
        description = RU_DESCRIPTIONS.get(f"{file}|{method_name}", description)
        rows.append(
            {
                "category": _category(module_dotted),
                "file": file,
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
