---
id: recover_stale_sensitive_action_lock
type: procedure_reference
document_state: current
version: 1.2
created: 2026-08-29
updated: 2026-09-04
---

# Восстановление после зависшей блокировки sensitive-action

## 1. Когда это нужно

[`OwnerControlGate`](../../src/owner_control/control.py) ([`ARC_CMP_002`](../../specifications/architecture_baseline.md#arc_cmp_002)) сериализует чувствительные действия через директорию-блокировку `owner_control_actions.lock` (`os.mkdir`, fail-closed). Крах процесса между созданием блокировки и её снятием оставляет блокировку навсегда: все последующие вызовы `authorize_sensitive_action` получают `OwnerControlStateError`, пока блокировка не будет снята вручную. Это осознанный fail-closed дизайн
([`AUD-013`](../../work/audit/audit_baseline_2026_08_29.md#aud-013)), а не баг — но без runbook он превращается в незадокументированную ловушку для владельца.

## 2. Диагностика

1. Найти директорию блокировки: `<state_dir>/owner_control_actions.lock`.
2. Прочитать `<state_dir>/owner_control_actions.lock/holder.json` — там записаны `pid` и `acquired_at` (UTC) процесса, который взял блокировку. Файла может не быть, если блокировка появилась до внедрения этого механизма.
3. **Подтвердить вне процесса восстановления, что держатель блокировки действительно мёртв** — не гадать по времени `acquired_at`:
   - `ps -p <pid>` (Linux/macOS) или эквивалент в среде контейнера/оркестратора;
   - логи контейнера/деплоя — не было ли перезапуска, OOM-kill, принудительной остановки;
   - если процесс всё ещё выполняется — это не зависшая блокировка, а раздел 3 не подходит.

## 3. Восстановление

Только после подтверждения из раздела 2:

```bash
python3.12 -m operations.scripts.owner_control.recover_lock <state_dir> \
    --confirm "REMOVE STALE OWNER CONTROL LOCK"
```

[`recover_stale_sensitive_action_lock()`](../../src/owner_control/control.py) дополнительно проверяет `holder.json` сам и отказывается снимать блокировку, если записанный `pid` всё ещё отвечает на `os.kill(pid, 0)` — команда с неверной confirmation-фразой или без записи о живом держателе не пройдёт. Отсутствие `holder.json` (блокировка создана до внедрения этого поля) не блокирует восстановление — решение о том, что процесс мёртв, остаётся на владельце, принявшем решение в разделе 2.

## 4. После восстановления

- Убедиться, что `authorize_sensitive_action` снова работает: любой некритичный тестовый вызов должен вернуть `AuthorizationDecision`, а не `OwnerControlStateError`.
- Если крах происходит регулярно — это отдельная проблема эксплуатации (нестабильность процесса/контейнера), а не повод ослаблять fail-closed поведение самой блокировки.
