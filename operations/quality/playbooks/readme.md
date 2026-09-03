---
id: quality_playbooks_readme
type: guide
document_state: current
applicability: normative
version: 1.1
updated: 2026-09-04
---

# Проверки качества

Исполняемые источники истины — [`quality_registry.json`](../../quality_registry.json), [`run_suite.py`](../../scripts/quality/run_suite.py) и [`project_check.yml`](../../../.github/workflows/project_check.yml). Playbook объясняет команды, но не объявляет дополнительные инструменты или расписания.

## Канонический запуск

```bash
python3.12 -m pip install --require-hashes -r operations/quality/requirements_dev.txt
python3.12 operations/scripts/quality/run_suite.py full
```

`full` включает документацию, security scan, dead-code diagnostic, Ruff, format check, MyPy baseline, unit tests с branch coverage, coverage policy, template/generated drift и health report. Фактический состав всегда читается из кода запуска.

## Playbooks

- [`documentation_audit.md`](documentation_audit.md) и [`documentation_rules_detailed.md`](documentation_rules_detailed.md);
- [`security_audit.md`](security_audit.md);
- [`dead_code_audit.md`](dead_code_audit.md);
- [`python_lint_check.md`](python_lint_check.md);
- [`python_type_check.md`](python_type_check.md);
- [`unit_tests.md`](unit_tests.md);
- [`integration_tests.md`](integration_tests.md);
- [`code_quality_check.md`](code_quality_check.md);
- [`pre_commit_validation.md`](pre_commit_validation.md);
- [`pre_push_validation.md`](pre_push_validation.md).

## TEST-карточки

Канонические спецификации доказательств:

- [`TEST_001`](../../../work/tests/test_001.md), [`TEST_002`](../../../work/tests/test_002.md), [`TEST_003`](../../../work/tests/test_003.md), [`TEST_004`](../../../work/tests/test_004.md), [`TEST_005`](../../../work/tests/test_005.md);
- [`TEST_006`](../../../work/tests/test_006.md), [`TEST_007`](../../../work/tests/test_007.md), [`TEST_008`](../../../work/tests/test_008.md), [`TEST_009`](../../../work/tests/test_009.md), [`TEST_010`](../../../work/tests/test_010.md);
- [`TEST_011`](../../../work/tests/test_011.md), [`TEST_012`](../../../work/tests/test_012.md), [`TEST_013`](../../../work/tests/test_013.md), [`TEST_014`](../../../work/tests/test_014.md), [`TEST_015`](../../../work/tests/test_015.md);
- [`TEST_016`](../../../work/tests/test_016.md), [`TEST_017`](../../../work/tests/test_017.md), [`TEST_018`](../../../work/tests/test_018.md), [`TEST_019`](../../../work/tests/test_019.md), [`TEST_020`](../../../work/tests/test_020.md).

Evidence считается действительным только для точного Git SHA и указанной среды. Локальный успех не выдаётся за результат CI.
