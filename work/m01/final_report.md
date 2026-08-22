---
id: m01_final_report
type: quality_evidence
evidence_state: superseded
version: 1.0
created: 2026-08-17
updated: 2026-08-22
acceptance_profiles:
  - foundation
---

# M01 — Рабочий отчёт о проверках

## 1. Статус документа

Этот файл не является доказательством готовности или принятия `m01`. Предыдущая редакция содержала вручную записанные количества требований, проверок и тестов, которые перестали соответствовать репозиторию. Она заменена этим уведомлением, чтобы устаревшие значения нельзя было использовать при принятии решения.

Фактические результаты должны формироваться автоматически для точного Git SHA и храниться в GitHub Actions artifact:

- `runtime/check_summary.json` — результат document checker;
- `runtime/test_output.txt` — результат unit-тестов;
- `runtime/evidence/latest.json` — SHA-bound evidence bundle;
- отдельная смысловая запись по [`semantic_review.md`](semantic_review.md).

## 2. Обязательная процедура

Перед предъявлением `m01` владельцу агент обязан:

1. Получить опубликованный Git SHA из проверяемой ветки или PR.
2. Убедиться, что Windows validation, Linux validation, Quality skills и общий `Project check` успешны для этого SHA.
3. Скачать evidence artifact именно этого запуска.
4. Проверить совпадение SHA, полный scope и отсутствие blockers.
5. Провести независимую смысловую проверку того же SHA.
6. Только после этого запросить подтверждение состава V1 и решение владельца.

Локальный зелёный прогон полезен до публикации, но не заменяет серверный artifact и не переводит `evidence_state` в `complete`.

## 3. Команды локальной проверки

```bash
python3.12 operations/scripts/documents/generate.py --all
python3.12 operations/scripts/documents/check.py --all
python3.12 -m unittest discover -s operations/tests -p "test_*.py"
bash .claude/skills/pre_commit_hook.sh
```

Расширенный quality-suite описан в [`.claude/skills/readme.md`](../../.claude/skills/readme.md). Его результаты также не должны копироваться в этот документ вручную: текущие числа берутся из машинного вывода конкретного запуска.

## 4. Условие замены

После успешной серверной проверки и смысловой проверки агент может создать новый финальный отчёт, который:

- ссылается на точный SHA и workflow run;
- не дублирует динамические количества вручную;
- содержит ссылки на evidence artifact;
- честно перечисляет оставшиеся gates;
- не заявляет готовность до фактического выполнения всех условий.
