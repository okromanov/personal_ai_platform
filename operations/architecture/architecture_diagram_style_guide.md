---
id: operations_architecture_diagram_style_guide
type: guide
document_state: current
version: 4.4
updated: 2026-09-16
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

Условный контрольный переход внутри компонента не становится новым `ARC_CMP_*` только потому, что показан отдельной карточкой.
Такая карточка визуально несёт ID родительского компонента и связывает каждый собственный выход с существующим `ARC_FLOW_*` или `SEC_CTL_*`.
Если карточка не получает номера слоя в левой колонке, она располагается между предыдущим и следующим нумерованными объектами с компактным просветом `transition-gap` с обеих сторон — по тому же ритму, что слой 01, плашка [`ARC_FLOW_001`](../../specifications/architecture_baseline.md#arc_flow_001) и слой 02. Оба отношения обозначаются `data-gap-from` и символическим `data-gap-kind="transition"`; числовое ожидаемое значение не дублируется в `data-*`-атрибуте, а вычисляется по формулам и геометрии шаблона из [`diagram_geometry_foundations.md`](diagram_geometry_foundations.md) §6.
Её локальные входы и выходы проводятся одним прямым сегментом, если между границами нет препятствия; такие пути помечаются `data-route="direct"` по правилу [`diagram_geometry_foundations.md`](diagram_geometry_foundations.md) §10.
В частности, «Выбор владельца» после Quality Gate относится к [`ARC_CMP_008`](../../specifications/architecture_baseline.md#arc_cmp_008), а коррекция с новым `Run` — к [`ARC_FLOW_001`](../../specifications/architecture_baseline.md#arc_flow_001).

## 3. Трассируемость и метаданные — архитектурная специфика

Формат блока метаданных и механизм проверки — [`diagram_geometry_foundations.md`](diagram_geometry_foundations.md) §13. Для архитектурной схемы:

- `source` — как правило [`architecture_baseline.md`](../../specifications/architecture_baseline.md), [`infrastructure_baseline.md`](../../specifications/infrastructure_baseline.md) и [`system_specification.md`](../../specifications/system_specification.md), в зависимости от того, какие ID изображены.
- `id` — одна строка на каждый реально изображённый `ARC_CMP_*`/`ARC_FLOW_*`/`SEC_CTL_*`/`INF_CMP_*`/`INF_FLOW_*`. Архитектурная схема, показывающая устойчивые компоненты, практически всегда несёт непустой список `id` — в отличие от процессной схемы, где список может быть пуст (см. [`process_diagram_style_guide.md`](process_diagram_style_guide.md) §2).
- Легенда перечисляет каждое из реально используемых семейств ID, включая `SEC_CTL_*`; полнота и отсутствие лишних семейств проверяются `diagram_lint.py`.
- Корневой `<svg>` несёт `data-diagram-kind="architecture"`. Для заполненного артефакта архитектурный профиль также распознаётся по заявленным `ARC_*`/`INF_*`/`SEC_CTL_*`; явный атрибут нужен шаблону без ID, чтобы те же проверки работали до заполнения.

## 4. Размещение файла

Архитектурные SVG размещаются в `work/artefacts/architecture/`. Остальные правила жизненного цикла (именование, SVG как редактируемый источник, обработка производных PNG/PDF/PPTX, критерий «правим существующую vs создаём новую», шаблонный скелет профиля) — [`diagram_geometry_foundations.md`](diagram_geometry_foundations.md) §15, включая шаблон `operations/architecture/templates/architecture_diagram_template.svg` (§15.1).

## 5. Чек-лист перед публикацией

Архитектурная схема обязана пройти чек-лист [`diagram_geometry_foundations.md`](diagram_geometry_foundations.md) §17 полностью. Дополнительно к нему:

1. Схема не смешивает архитектурный профиль с процессным (раздел 2) — варианты исхода показаны портами/контрактами, не ромбом решения.
2. Каждый `id` в метаданных сверен построчно с текстом соответствующего раздела [`architecture_baseline.md`](../../specifications/architecture_baseline.md)/[`system_specification.md`](../../specifications/system_specification.md)/[`infrastructure_baseline.md`](../../specifications/infrastructure_baseline.md), включая заданный спецификацией порядок/цепочку зависимостей.
3. Файл размещён в `work/artefacts/architecture/` (раздел 4).
4. При завершении TASK пройдена автоматическая проверка влияния результата; если она перечисляет затронутые ID, изменено графическое тело схемы и увеличен `diagram_version`, а не только метаданные.
5. Каждый самостоятельный переходный блок показывает ID родительского компонента, а его внешние подписи и коннекторы связаны с существующим потоком или контролем.
