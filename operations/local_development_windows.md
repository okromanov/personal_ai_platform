---
id: operations_local_development_windows
type: operations_guide
document_state: current
version: 1.1
updated: 2026-08-24
traces_to:
  - ADR_001
---

# Локальная разработка в Windows

## 1. Назначение

Документ описывает минимальную локальную среду для работы с репозиторием в Windows. VS Code и GitHub Desktop не являются обязательными.

Связанные материалы:

- процесс: [`operations/change_process.md`](../operations/change_process.md);
- текущий этап: [`milestones.md`](../milestones.md);
- инструкция агенту разработки: [`AGENTS.md`](../AGENTS.md);
- переход принятия: [`acceptance.md`](acceptance.md);
- текущий экран владельца: [`project_status.md`](../project_status.md);
- операционные проверки: [`work/tests/`](../work/tests/).

## 2. Требования к компьютеру

Нужны:

- Git for Windows;
- Python 3.12+, соответствующий зафиксированному кандидату [`ADR_001`](../adr/adr_001_language_and_runtime.md), который станет `accepted` только при принятии [`m01`](../milestones.md#m01);
- PowerShell 5.1+ или современный PowerShell;
- доступ к приватному репозиторию GitHub.

Редактор выбирается свободно.

## 3. Базовая диагностика

Команды выполняются из корня репозитория:

```powershell
$ProjectRoot = (git rev-parse --show-toplevel).Trim()
Set-Location $ProjectRoot

Write-Host "root: $ProjectRoot"
Write-Host "branch: $((git branch --show-current).Trim())"
git status --short
git log -1 --oneline
py --version
git --version
```

Перед изменениями рабочая копия должна быть понятной: неожиданные локальные изменения не удаляются автоматически.

## 4. Основные команды проекта

Полная локальная проверка проекта:

```powershell
py operations\scripts\quality\run_suite.py full
```

Эта же последовательность выполняется в [`.github/workflows/project_check.yml`](../.github/workflows/project_check.yml) для запроса на слияние. Процесс имеет только право чтения и не получает рабочие секреты.

Отдельная генерация производных файлов:

```powershell
py operations\scripts\documents\generate.py --all
```

Проверка документации и правил управления:

```powershell
py operations\scripts\documents\check.py --all
```

Автоматические технические тесты:

```powershell
py operations\scripts\quality\run_unittests.py --verbose
```

Локальный прогон является диагностикой и не создаёт принимаемое серверное доказательство. Канонический bundle создаёт только GitHub Actions с обязательными `server_source` и точным event SHA.

Проверка готовности и атомарный старт подготовленного этапа:

```powershell
py operations\scripts\milestones\start.py --milestone mXX --dry-run
py operations\scripts\milestones\start.py --milestone mXX --apply
```

## 5. Принятие владельцем

Для каждого этапа артефакт GitHub Actions сначала должен содержать `ready-for-semantic-review`. Затем свежий проверяющий выполняет смысловую проверку с результатом `pass` на том же SHA (для [`m01`](../milestones.md#m01) он дополнительно подтверждает состав V1). Только после этого владелец может дать `ПРИНИМАЮ mXX`.

Создаётся отдельная ветка от точного SHA доказательства. Нужные файлы помещаются локально в `runtime/evidence/`.

```powershell
py operations\scripts\acceptance\apply.py --milestone mXX --owner-confirmation "ПРИНИМАЮ mXX" --evidence runtime\evidence\latest.json --semantic-review runtime\evidence\mXX_semantic_review.json --evidence-repository owner/repo --evidence-workflow "Project check" --evidence-run-id 123 --evidence-run-url https://github.com/owner/repo/actions/runs/123 --evidence-event-sha <40-char-sha> --evidence-artifact-id 456 --evidence-artifact-digest <sha256>
```

Скрипт только готовит разницу. После него нужно проверить `git diff`, выполнить полную проверку проекта и открыть обычный запрос на слияние. Прямой переход состояния в `main` запрещён.

## 6. Правила локальной работы

- Команды запускаются из корня репозитория.
- Перед потенциально разрушительными Git-операциями проверяется `git status --short`.
- Секреты находятся вне Git.
- Неожиданные локальные изменения не разрешаются и не удаляются автоматически.
- Производные файлы должны пересоздаваться из первичных источников.
- Доказательство от другого Git SHA не используется для принятия текущей рабочей копии.
- При ошибке владельцу или ассистенту передаётся полный относящийся к проблеме вывод без секретов.
