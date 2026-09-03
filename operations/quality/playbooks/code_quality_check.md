---
id: code_quality_check
type: guide
document_state: current
applicability: normative
version: 1.4
updated: 2026-09-03
---

# Полный code-quality gate

## Команда

```bash
python3.12 operations/scripts/quality/run_suite.py full
```

## Состав

Состав строится из исполняемого [`run_suite.py`](../../scripts/quality/run_suite.py): документация, security, dead code, Ruff, format, MyPy, тесты, coverage, template/generated drift и health. Playbook не копирует версии инструментов и число проверок.

## Результат

Успех — код 0 и созданные runtime-артефакты для текущего SHA. Health report с пометкой о грязном рабочем дереве допустим во время локальной разработки и не заменяет чистый commit/CI evidence.

Любая ошибка блокирует публикацию до исправления причины.
