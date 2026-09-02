---
id: operations_architecture_diagram_style_guide
type: guide
document_state: current
version: 4.0
updated: 2026-09-01
depends_on:
  - project_rules
  - architecture_baseline
  - infrastructure_baseline
  - system_specification
  - operations_change_process
  - operations_diagram_geometry_foundations
---

# Правила оформления архитектурных схем

## 1. Назначение

Документ фиксирует правила, специфичные именно для архитектурных SVG-схем — профилей «Архитектурный обзор» и «Архитектурная детализация» из [`diagram_geometry_foundations.md`](diagram_geometry_foundations.md) §3. Геометрия, токены, типографика, язык, карточки, связи, цвет, легенда, доступность, трассируемость/метаданные, файлы и рабочий процесс в общем случае — там же, этот документ их не повторяет.

Схема является представлением утверждённых документов, а не самостоятельным источником истины. При расхождении со спецификацией, baseline, ADR или правилами проекта приоритет имеет текстовый источник.

## 2. Архитектурная специфика профиля

Архитектурная схема не изображает внутренний алгоритм как последовательность процессных шагов — для этого есть [`process_diagram_style_guide.md`](process_diagram_style_guide.md). В архитектурной схеме варианты выхода показываются интерфейсами, портами или контрактами результата, а не процессным ромбом.

Для текущей общей архитектуры основная колонка сохраняет десятислойную структуру, определённую baseline. Нумерация слоёв отражает логический порядок представления, а не номера `ARC_CMP_*`.

## 3. Трассируемость и метаданные — архитектурная специфика

Формат блока метаданных и механизм проверки — [`diagram_geometry_foundations.md`](diagram_geometry_foundations.md) §13. Для архитектурной схемы:

- `source` — как правило [`architecture_baseline.md`](../../specifications/architecture_baseline.md), [`infrastructure_baseline.md`](../../specifications/infrastructure_baseline.md) и [`system_specification.md`](../../specifications/system_specification.md), в зависимости от того, какие ID изображены.
- `id` — одна строка на каждый реально изображённый `ARC_CMP_*`/`ARC_FLOW_*`/`SEC_CTL_*`/`INF_CMP_*`/`INF_FLOW_*`. Архитектурная схема, показывающая устойчивые компоненты, практически всегда несёт непустой список `id` — в отличие от процессной схемы, где список может быть пуст (см. [`process_diagram_style_guide.md`](process_diagram_style_guide.md) §2).

## 4. Размещение файла

Архитектурные SVG размещаются в `work/artefacts/architecture/`. Остальные правила жизненного цикла (именование, SVG как редактируемый источник, обработка производных PNG/PDF/PPTX, критерий «правим существующую vs создаём новую») — [`diagram_geometry_foundations.md`](diagram_geometry_foundations.md) §15.

## 5. Чек-лист перед публикацией

Архитектурная схема обязана пройти чек-лист [`diagram_geometry_foundations.md`](diagram_geometry_foundations.md) §17 полностью. Дополнительно к нему:

1. Схема не смешивает архитектурный профиль с процессным (раздел 2) — варианты исхода показаны портами/контрактами, не ромбом решения.
2. Каждый `id` в метаданных сверен построчно с текстом соответствующего раздела [`architecture_baseline.md`](../../specifications/architecture_baseline.md)/[`system_specification.md`](../../specifications/system_specification.md)/[`infrastructure_baseline.md`](../../specifications/infrastructure_baseline.md), включая заданный спецификацией порядок/цепочку зависимостей.
3. Файл размещён в `work/artefacts/architecture/` (раздел 4).
