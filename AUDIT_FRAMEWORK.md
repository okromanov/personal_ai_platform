---
id: audit_framework
type: instruction
document_state: current
version: 1.0
updated: 2026-08-25
applies_to: personal_ai_platform
depends_on:
  - AGENTS.md
  - project_rules.md
  - project_status.md
---

# Фреймворк комплексного аудита репозитория
## Для: vibe coder + AI агенты (Cursor, Claude Code, Windsurf)

---

## ЦЕЛЬ АУДИТА

Провести проверку контракта между вами и AI-агентами через призму **`AGENTS.md`** как единого источника истины.

**Вопросы, на которые аудит отвечает:**
1. ✅ **AGENTS.md актуален и истинен?** (или это фантазия?)
2. ✅ **Агенты реально соблюдают написанные правила?** (или их игнорируют?)
3. ✅ **Код соответствует требованиям?** (specifications/*, AGENTS.md, project_rules.md)
4. ✅ **Нет ли скрытого технического долга, заглушек, хардкода?**
5. ✅ **Архитектура остаётся современной и эффективной?**
6. ✅ **Контракты между компонентами честны?** (или полны оптимизма?)

---

## СТРУКТУРА ПРОЕКТА (для навигации)

```
/home/user/personal_ai_platform/
├── AGENTS.md                          ← Контракт с агентами (ОСНОВНОЕ)
├── project_rules.md                   ← Принципы и иерархия
├── project_status.md                  ← Текущее состояние (для владельца)
├── tasks.md                           ← Сводка активных TASK
├── milestones.md                      ← Этапы проекта (m01-m06)
│
├── specifications/                    ← Источники истины (не код!)
│   ├── business_requirements.md       ← Что нужно (BR_001-039)
│   ├── system_specification.md        ← Как система работает (SYS_*)
│   ├── architecture_baseline.md       ← Как устроена архитектура (ARC_CMP_*)
│   ├── infrastructure_baseline.md     ← Инфраструктура (INF_*)
│   └── threat_model.md                ← Угрозы и контроли (THR_*, SEC_CTL_*)
│
├── adr/                               ← Архитектурные решения
│   └── adr_NNN_*.md                   ← Каждое решение (ADR_*)
│
├── work/                              ← Рабочие материалы
│   ├── tasks/                         ← TASK карточки (TASK_*)
│   │   └── task_NNN_*.md
│   ├── tests/                         ← Тестовые карточки (TEST_*)
│   │   └── test_NNN.md
│   ├── acceptance/                    ← Сценарии приёма
│   └── m01_final_report.md
│
├── operations/                        ← Процедуры и автоматизация
│   ├── AGENTS.md (ссылка на корень)   ← Инструкция агентам
│   ├── change_process.md              ← Как менять код (ветки, PR, checks)
│   ├── procedure_map.md               ← Wizard для частых ситуаций
│   ├── acceptance.md                  ← Как принимать работу
│   ├── semantic_review.md             ← Критический анализ
│   ├── setup_precommit.md             ← pre-commit hook (критично!)
│   ├── adr_lifecycle.md               ← Как работать с ADR
│   ├── state_machines.md              ← Машины состояний (TASK, TEST)
│   ├── threat_review_triggers.md      ← Когда проверять угрозы
│   │
│   ├── quality/                       ← Проверки качества
│   │   ├── requirements_dev.txt       ← Зависимости
│   │   ├── requirements_test.txt
│   │   └── requirements_lint.txt
│   │
│   ├── scripts/quality/               ← Скрипты проверок
│   │   └── run_suite.py               ← ГЛАВНЫЙ: запускает все проверки
│   │
│   ├── templates/                     ← Шаблоны документов
│   ├── hooks/                         ← Git hooks
│   └── tests/                         ← Встроенные тесты проверок
│
├── src/                               ← Исходный код (Python)
│   ├── orchestration/                 ← Оркестровка, runtime
│   ├── models/                        ← LLM адаптеры
│   ├── channels/                      ← Telegram, др. каналы
│   ├── tools/                         ← Registry инструментов
│   └── owner_control/                 ← Управление владельцем
│
├── generated/                         ← ГЕНЕРИРУЕМЫЕ файлы (не редактировать!)
│   ├── repository_structure.md        ← Автоматическое дерево репо
│   ├── traceability_matrix.md         ← Кто что реализует
│   ├── markdown_index.md              ← Индекс всех .md файлов
│   ├── test_catalog.md                ← Каталог тестов
│   ├── health_check_report.md         ← Результаты checks
│   └── non_markdown_index.md          ← Индекс кода
│
└── .claude/                           ← Конфигурация Claude Code
    └── settings.json
```

---

## 6 СТОЛПОВ АУДИТА

### 1️⃣ AGENTS.md как контракт (Contract Audit)

**Что проверяем:**
- Все ли ссылки на файлы в AGENTS.md указывают на реально существующие файлы?
- Не противоречат ли друг другу разделы AGENTS.md?
- Охватывает ли AGENTS.md все ключевые части кодовой базы?
- Соответствуют ли примеры кода в AGENTS.md реальному коду?
- Нет ли в AGENTS.md "фантазий" (описаний того, что не реализовано)?

**Чек-лист:**
- [ ] Прочитана вся цепочка ссылок: AGENTS.md → project_rules.md → specifications/* → operations/*
- [ ] Открыты в редакторе все файлы, на которые ссылается AGENTS.md
- [ ] Проверены якоря: все `[`ID`](#id)` ведут на реально существующие якоря
- [ ] Нет конфликтов между "рекомендуемым подходом" в одном разделе и "запретом" в другом
- [ ] Все процедуры из AGENTS.md (run_suite.py, pre-commit hook и др.) реально существуют и работают

**Если проблемы найдены:** Раздел 7.A "Обновить контракт"

---

### 2️⃣ Alignment: Соблюдение контракта в коде

**Что проверяем:**
- Код делает то, что написано в AGENTS.md и specifications/?
- Или агент "галлюцинировал" и написал по-своему?
- Структура папок/файлов соответствует архитектуре?
- Стиль кода соответствует project_rules.md?

**Примеры нарушений:**
- AGENTS.md: "используем попаттерн X для модуля Y" → В коде используется Z
- specifications/architecture_baseline.md: "Компоненты: A, B, C" → В src/ найдены D, E, F
- project_rules.md: "Имена переменных snake_case" → В коде camelCase

**Чек-лист:**
- [ ] Проверены все модули из ARC_CMP_* в specifications/architecture_baseline.md
- [ ] Для каждого модуля: папка существует, структура соответствует описанию
- [ ] Проверены все требования (BR_*) из specifications/business_requirements.md
- [ ] Для каждого BR: найдена TASK, которая его реализует, найден код
- [ ] Проверены все нелюбимые паттерны из project_rules.md раздел 2 (запреты)

**Если проблемы найдены:** Раздел 7.B "Повысить alignment"

---

### 3️⃣ Качество кода и Best Practices

**Что проверяем:**
- Используются ли актуальные паттерны для Python 3.12+?
- Соблюдается ли SOLID, DRY, KISS?
- Есть ли очевидные узкие места (N+1, неоптимальные алгоритмы)?
- Есть ли мёртвый код (imports, функции, которые никто не использует)?

**Чек-лист:**
- [ ] Запущен `python3.12 operations/scripts/quality/run_suite.py full`
- [ ] Все проверки зелёные (lint, format, type, complexity)
- [ ] Проверена цикломатическая сложность функций (не более 10)
- [ ] Нет явных узких мест (list comprehension вместо loop, кэширование повторных вызовов)
- [ ] Нет очевидных дублирований (одна логика копируется 3+ раза)

**Инструменты:**
- `pylint` / `flake8` — стиль и ошибки
- `black` — форматирование
- `mypy` — типизация
- `radon` — цикломатическая сложность
- `bandit` — безопасность

---

### 4️⃣ Зачистка: Заглушки, Хардкод и Мусор

**КРИТИЧНО!** Это "no BS" политика проекта. Заглушки допустимы ТОЛЬКО в:
- Тестах (моки, fixtures)
- Явно помеченных прототипах (v0, draft)

**Что ищем:**
```python
# ❌ ПЛОХО (в продакшене)
TODO("реализуем позже")
FIXME: неправильный результат
HACK: обход для теста
try: ...
except: pass  # ← скрыть ошибку
if some_condition:
    return None  # ← вместо обработки
# ... (три точки, заглушка)
```

```python
# ❌ ПЛОХО (хардкод)
url = "http://192.168.1.1:8080"
token = "sk_live_abc123xyz"
path = "/home/user/data"
TIMEOUT = 30
```

```python
# ✅ ХОРОШО (конфиг)
url = os.getenv("RUNTIME_URL", "http://localhost:8080")
token = os.getenv("RUNTIME_TOKEN")  # обязательно
path = os.getenv("DATA_PATH", "./data")
TIMEOUT = int(os.getenv("TIMEOUT", "30"))
```

**Чек-лист:**
- [ ] Глобальный grep по репо: `grep -rn "TODO\|FIXME\|HACK" src/`
  - Каждое найденное: либо TASK карточка, либо удалить
- [ ] `grep -rn "except.*pass\|# .*\.\.\.\|return None" src/`
  - Проверить: это нужно или заглушка?
- [ ] Нет ли в коде hardcoded: URL, IP, пути к файлам, токены
  - Всё должно быть в .env / os.getenv()
- [ ] Нет ли в логах чувствительных данных (tokens, passwords)

**Инструмент для поиска секретов:**
```bash
python3.12 -m pip install detect-secrets
detect-secrets scan src/
```

**Если проблемы найдены:** Раздел 7.C "Зачистка кода"

---

### 5️⃣ Тесты, CI/CD и Надежность

**Что проверяем:**
- Какие части бизнеса **не** покрыты тестами?
- Есть ли flaky тесты (проходят/падают случайно)?
- Работает ли CI/CD pipeline? Блокирует ли он мёртвый код?
- Есть ли тесты на edge cases и ошибки, или только happy path?

**Чек-лист:**
- [ ] Все TASK карточки имеют TEST карточки? (`work/tests/test_NNN.md`)
- [ ] Для каждого модуля (src/orchestration/, src/models/ и т.д.) есть unit-тесты?
- [ ] Покрытие кода: `pytest --cov=src --cov-report=html`
  - Целевое: ≥80% для критических модулей
- [ ] Нет ли игнорируемых тестов (`@pytest.mark.skip`, `@pytest.mark.xfail` без TASK)?
- [ ] Проверены ли edge cases? (пустой вход, None, ошибки вызовов, timeout)
- [ ] Есть ли integration тесты между компонентами (src/orchestration + src/models)?

**Инструмент:**
```bash
python3.12 operations/scripts/quality/run_suite.py full
# Видит: unit тесты, линт, type check, покрытие, форматирование
```

**Если проблемы найдены:** Раздел 7.D "Улучшить тестирование"

---

### 6️⃣ Связность кодовой базы (Cohesion & Traceability)

**Что проверяем:**
- Каждый модуль делает одно? Или мешанина ответственности?
- Каждый BR_* из requirements реально реализован?
- Каждый TASK реально реализован в коде?
- Нет ли "мёртвых" файлов (никто их не импортирует)?

**Инструмент: Traceability Matrix**
```
BR_001 (требование) 
  ↓ (implements)
TASK_003 (карточка)
  ↓ (code)
src/orchestration/orchestrator.py (реализация)
  ↓ (covers)
TEST_003 (тест)
  ↓ (verifies)
BR_001 ✅
```

**Чек-лист:**
- [ ] Открыт сгенерированный файл: `generated/traceability_matrix.md`
- [ ] Все BR_* имеют `implements` ссылку на TASK
- [ ] Все TASK имеют `traces_to` ссылку на BR_*
- [ ] Нет ли TASK без `allowed_paths` (висящие карточки)
- [ ] Все TEST имеют `verifies` ссылку на BR_* или TASK
- [ ] Нет ли в src/ модулей, которые не импортирует ничего (мёртвый код)

**Команда для поиска мёртвого кода:**
```bash
# Просмотр всех файлов в src/
find src -name "*.py" | while read f; do
  if ! grep -r "from.*$f\|import.*$f" src/ --exclude-dir=__pycache__ >/dev/null; then
    echo "Possible dead: $f"
  fi
done
```

**Если проблемы найдены:** Раздел 7.E "Повысить связность"

---

## ПОРЯДОК ПРОВЕДЕНИЯ АУДИТА

### Этап 1: Быстрая проверка (15 мин)
1. Открыть `AGENTS.md`, `project_rules.md`, `project_status.md`
2. Запустить: `python3.12 operations/scripts/quality/run_suite.py full`
3. Открыть `generated/health_check_report.md`
4. Вердикт: "Красный" / "Жёлтый" / "Зелёный"

### Этап 2: Проверка контракта (30 мин)
1. Пройти по Столпу 1 и Столпу 2 (см. выше)
2. Для каждой ссылки в AGENTS.md: файл существует?
3. Для каждого модуля в architecture_baseline.md: есть в src/?

### Этап 3: Глубокий анализ кода (60+ мин)
1. Столп 3: Качество кода (запустить линтеры, найти узкие места)
2. Столп 4: Заглушки и хардкод (grep + manual review)
3. Столп 5: Тесты и покрытие
4. Столп 6: Связность (traceability)

### Этап 4: Отчёт и план (30 мин)
1. Составить список проблем по приоритету
2. Раздел 7: Plan of Action

---

## ОТЧЁТ ОБ АУДИТЕ (Шаблон)

### 📊 Executive Summary

- **Общая оценка здоровья:** [1-10]
- **Здоровье контракта (AGENTS.md):** [1-10]
- **Вердикт:** (одно предложение — где проблема, если есть)
- **Главное достижение:** (что реально работает хорошо)

---

### 🚨 Критические проблемы (Блокеры)

Если нет — напиши: **Не обнаружено**

Иначе:
- **Проблема:** [Название]
- **Где:** [Файл, строка]
- **Почему плохо:** [Последствия]
- **Как исправить:** [Конкретные шаги]

---

### 📜 Состояние контракта (AGENTS.md)

**Битые ссылки:**
- Файлы, на которые ссылается AGENTS.md, но которых нет в репо
- Якоря, которые указаны, но не существуют

**Устаревшие описания:**
- Разделы AGENTS.md, которые не соответствуют реальному коду
- Примеры, которые не работают

**Тёмные углы:**
- Важные модули/файлы в src/, про которые в AGENTS.md ничего не сказано
- Новые требования, которые не описаны в specifications/

**Противоречия:**
- Конфликты внутри AGENTS.md
- Конфликты между AGENTS.md и project_rules.md

---

### 🎭 Нарушения контракта (Alignment Issues)

Для каждого нарушения:
- **В AGENTS.md сказано:** X
- **В коде src/...:** Y
- **Рекомендация:** Обновить AGENTS.md ИЛИ переписать код (что правильнее?)

---

### 🧹 Зачистка: Заглушки и Хардкод

Для каждой находки:
- **Файл, строка:** X:Y
- **Найдено:** `...code...`
- **Статус:** Заглушка / Хардкод / Мусор / Мёртвый код
- **Действие:** Удалить / TASK / Вынести в .env

---

### 🏗 Архитектура и Best Practices

**Что работает хорошо:**
- [Паттерны, которые правильно реализованы]

**Устаревшие подходы:**
- **Найдено в файле X:** [Паттерн A]
- **Альтернатива (актуальная):** [Паттерн B]
- **Выигрыш:** [Что улучшится]

---

### 🧪 Тесты, CI/CD и Надежность

**Слепые зоны:**
- Какие BR_* / модули не покрыты тестами
- Какие edge cases не тестируются

**Flaky тесты:**
- Список тестов, которые иногда падают

**Что не хватает в CI/CD:**
- Какие проверки нужно добавить

---

### 🎯 Action Plan (План действий)

#### A. Обновить контракт (AGENTS.md)

Для каждого изменения:
```markdown
- [ ] Раздел "X"
  - Убрать: [что удалить или исправить]
  - Добавить: [что дописать]
  - Ссылка: [на какой файл]
  - Примерный текст:
    ```
    [новый текст для AGENTS.md]
    ```
```

#### B. Адаптировать код под контракт

Готовый промт для агента:
```markdown
Контекст: Аудит выявил, что в модуле X код не соответствует AGENTS.md.

Текущее состояние (AGENTS.md):
[цитата из AGENTS.md]

Реальное состояние кода:
[цитата из src/...]

Требуется:
1. [Конкретное действие 1]
2. [Конкретное действие 2]
3. Обновить работу в TASK_NNN

Файлы для изменения:
- src/.../file.py (строки X-Y)
- src/.../test_file.py (добавить тест Z)

После завершения:
- run_suite.py full должен быть зелёным
- Обновить TASK_NNN.md: `work_state: completed`
```

#### C. Зачистка кода

```markdown
1. Удалить заглушки:
   - src/file.py:123 `# TODO: ...` → Либо TASK, либо удалить

2. Вынести хардкод в .env:
   - src/file.py:456 `url = "http://192.168.1.1"`
   - Команда: grep -rn "http://\|sk_live" src/ | grep -v test
   - Пример .env:
     ```
     RUNTIME_URL=http://localhost:8080
     RUNTIME_TOKEN=sk_live_xxx
     ```

3. Удалить мёртвый код:
   - src/unused_module.py (не импортирует ничего)
   - Команда удаления: git rm src/unused_module.py
```

#### D. Настроить процессы (один раз)

```markdown
1. Pre-commit hook:
   bash operations/setup_precommit.md
   
2. CI/CD проверки:
   - Убедиться, что .github/workflows/ запускает run_suite.py
   - Добавить проверку: detect-secrets scan src/
   - Добавить проверку: traceability validation

3. Регулярные проверки:
   - Раз в неделю: run_suite.py full
   - Раз в месяц: аудит alignment (это фреймворк)
```

---

## ПОЛЕЗНЫЕ КОМАНДЫ

```bash
# Установить зависимости
python3.12 -m pip install -r operations/quality/requirements_dev.txt

# Запустить ВСЕ проверки
python3.12 operations/scripts/quality/run_suite.py full

# Установить pre-commit hook
bash operations/setup_precommit.md

# Поиск TODO, FIXME, заглушек
grep -rn "TODO\|FIXME\|HACK\|pass\|return None" src/

# Поиск хардкода (URL, IP, токены)
grep -rn "http://\|sk_live_\|192\.168" src/

# Поиск потенциальных секретов
python3.12 -m pip install detect-secrets
detect-secrets scan src/

# Мёртвый код (необъявленные импорты)
find src -name "*.py" -exec grep -l "def " {} \; | while read f; do
  if ! grep -r "from.*import.*\|import" src/ --include="*.py" | grep -q "$f"; then
    echo "Possible dead: $f"
  fi
done

# Покрытие тестами
pytest --cov=src --cov-report=html operations/tests/

# Трассируемость
cat generated/traceability_matrix.md
```

---

## КЛЮЧЕВЫЕ ДОКУМЕНТЫ (Входная точка для каждого анализа)

| Вопрос | Документ | Поиск в | 
|--------|----------|---------|
| Какие правила? | `project_rules.md` | §1, §2 (запреты), §3 (иерархия) |
| Какой контракт? | `AGENTS.md` | Весь файл |
| Что нужно? | `specifications/business_requirements.md` | `BR_*` |
| Какая угроза? | `specifications/threat_model.md` | `THR_*`, `SEC_CTL_*` |
| Какая архитектура? | `specifications/architecture_baseline.md` | `ARC_CMP_*` |
| Какой статус? | `project_status.md` | Текущие TASK, blockers |
| Какие TASK? | `work/tasks/task_*.md` | Активные карточки |
| Какие тесты? | `work/tests/test_*.md` | Покрытие, evidence |
| Какие решения? | `adr/adr_*.md` | ADR_* карточки |
| Как менять? | `operations/change_process.md` | Ветки, PR, слияние |

---

## КРАСНЫЕ ФЛАГИ (что-то НЕ ТАК)

❌ AGENTS.md не обновлялся более месяца  
❌ `run_suite.py full` падает или дольше 2 минут  
❌ В коде есть `except: pass` или `# TODO` без TASK  
❌ Есть захардкоженные URL, токены, пути  
❌ Трассируемость разорвана (BR без TASK, TASK без TEST)  
❌ В `generated/health_check_report.md` более 2 красных строк  
❌ Большой gap между тем, что в AGENTS.md, и реальным кодом  
❌ Нет pre-commit hook или он не блокирует коммиты  

---

## УТИЛИТЫ И АВТОМАТИЗАЦИЯ

Все скрипты находятся в `operations/scripts/quality/`:

```python
# run_suite.py — главный скрипт проверок
python3.12 operations/scripts/quality/run_suite.py full

# check.py — проверка документов (вызывается из hook)
python3.12 operations/scripts/check.py --all

# collect_evidence.py — сбор доказательств для TEST карточек
python3.12 operations/scripts/collect_evidence.py

# Все эти инструменты настроены в .claude/settings.json
cat .claude/settings.json
```

---

## ВЕРСИЯ ЭТОГО ФРЕЙМВОРКА

- **Версия:** 1.0
- **Применимо к:** personal_ai_platform
- **Зависит от:** AGENTS.md v2.4+
- **Последнее обновление:** 2026-08-25

**Обновлять этот файл, если:**
- Структура проекта существенно меняется
- Добавлены новые столпы аудита или процедуры
- Выявлены новые типичные ошибки агентов
