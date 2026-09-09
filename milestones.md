---
id: project_milestones
type: roadmap
document_state: current
version: 2.4
updated: 2026-09-09
depends_on:
  - business_requirements
  - architecture_baseline
  - infrastructure_baseline
  - candidate_skill_lifecycle
  - candidate_tool_lifecycle
---

# Этапы развития personal_ai_platform

## 1. Назначение

Документ является единственным источником ответа на вопрос: **что и когда делаем, какой состав входит в очередной этап и какими доказательствами подтверждается готовность**.

Состав этапа перечисляет требования: `BR_*`, `SYS_*`, `SEC_CTL_*` и `INF_REQ_*`. Архитектурные и инфраструктурные компоненты и потоки в состав не входят: они являются способом реализации и проверяются через требования, на которые ссылаются. Отсутствие `ARC_*`, `INF_CMP_*` и `INF_FLOW_*` в составе не означает, что они не подтверждаются.

Бизнес-требования, системные требования, архитектура, меры безопасности и инфраструктурные требования не содержат номера версии поставки. Этап выбирает временной срез этих устойчивых элементов, но не переопределяет их смысл. Общие правила формирования, состояния и приёмки этапа определены только в [`operations/change_process.md`](operations/change_process.md#7-границы-и-пересмотр-спецификаций).

## 2. Периметр V1

V1 — первый регулярно используемый персональный помощник владельца. Его поставка завершается после [`m06`](#m06).

**Источник истины:** Периметр V1 определяется единственным правилом: V1 включает все бизнес-требования с приоритетом `core` согласно [`business_requirements.md`](specifications/business_requirements.md) на момент принятия этапа. Нет отдельного решения о составе — состав автоматически следует из приоритетов требований.

**Обоснование:** приоритет `core` означает, что без требования целевой помощник теряет основной смысл, поэтому оно не может быть отложено за пределы первой регулярно используемой версии. Изменение периметра выполняется изменением приоритета требования в [`business_requirements.md`](specifications/business_requirements.md), что немедленно влияет на V1.

Другие бизнес-требования остаются действительными потребностями продукта, но не блокируют приёмку V1. Их порядок после V1 определяется заново на этапе [`m07`](#m07).

После завершения смысловой проверки, но перед окончательным принятием [`m01`](#m01), владелец явно подтверждает перечисленный выше периметр командой `ПОДТВЕРЖДАЮ СОСТАВ V1` либо возвращает его на пересмотр командой `ИЗМЕНИ СОСТАВ V1: <что включить или исключить>`. Смысловая запись сохраняет точный список подтверждённых ID, поэтому команда не содержит вручную поддерживаемые количества. Автоматическая проверка не может принять это продуктовое решение за владельца.

<a id="m01"></a>
## m01 — Согласованная и проверяемая основа проекта

- work_state: `completed`
- результат: непротиворечивая базовая редакция документов, трассировки, шаблонов и автоматических проверок до начала основного продуктового кода. Номер версии отдельного документа отражает его собственную историю и не обязан равняться `1.0`.
- состав основы: первичные документы, шаблоны, типизированная трассировка, средства проверки качества и принятия. Машинная область файлов задаётся профилем `foundation` в [`operations/quality_registry.json`](operations/quality_registry.json). Этап [`m01`](#m01) **не означает реализацию продуктовых BR/SYS/SEC/INF**.
- ADR этого этапа: [`ADR_001`](adr/adr_001_language_and_runtime.md#adr_001), [`ADR_002`](adr/adr_002_core_runtime_boundary.md#adr_002), [`ADR_003`](adr/adr_003_model_provider_interface.md#adr_003), [`ADR_004`](adr/adr_004_task_events_and_logging.md#adr_004).
- обязательные автоматические доказательства: [`TEST_001`](work/tests/test_001.md), [`TEST_002`](work/tests/test_002.md).
- обязательное доказательство владельца перед `ПРИНИМАЮ m01`: смысловая проверка базовой редакции на точном Git SHA по процедуре [`operations/semantic_review.md`](operations/semantic_review.md#обязательная-смысловая-проверка-при-принятии-этапа).

### Подэтапы

1. Развести источники истины по одному главному вопросу и убрать повтор плана этапов и деталей реализации.
2. Перенумеровать устойчивые идентификаторы и создать отдельный шаблон для каждого трассируемого типа.
3. Построить типизированный граф трассировки и отрицательные проверки отсутствующих, повторных и оборванных связей.
4. Подключить декларативный реестр качества и убедиться, что отсутствие обязательного доказательства блокирует готовность.
5. Получить зелёный полный прогон проверок на текущем Git SHA.

### Техническая готовность основы

До предъявления [`m01`](#m01) владельцу должны одновременно выполняться условия:

- полный локальный прогон `generate.py --all`, `check.py --all` и unit-тестов успешен;
- [`TEST_001`](work/tests/test_001.md) и [`TEST_002`](work/tests/test_002.md) подтверждены evidence bundle на точном Git SHA;
- обязательные проверки GitHub Actions для того же SHA успешны;
- отсутствуют неразрешённые замечания, блокирующие приёмку;
- документы соответствуют правилам безопасности и доверия из [`AGENTS.md`](AGENTS.md).

Невыполненное условие означает, что техническая готовность ещё не подтверждена. Фактическое состояние показывается в [`project_status.md`](project_status.md), а не кодируется символами готовности в этом нормативном перечне.

### Готовность этапа m01

Готовность [`m01`](#m01) означает, что основу можно предъявить владельцу единым пакетом. Помимо технической готовности обязательны:

- смысловая проверка по [`operations/semantic_review.md`](operations/semantic_review.md#обязательная-смысловая-проверка-при-принятии-этапа) на том же Git SHA;
- явное согласие владельца по составу V1 командой `ПОДТВЕРЖДАЮ СОСТАВ V1`.

Эти пункты являются критериями, а не отметкой их фактического выполнения. До их подтверждения [`m01`](#m01) остаётся `in-progress`.

Состояние `completed` появляется только после решения владельца `ПРИНИМАЮ m01` и контролируемого перехода принятия по [`operations/acceptance.md`](operations/acceptance.md).

<a id="m02"></a>
## m02 — Выбор ключевых технологий и первый живой помощник

- work_state: `in-progress`
- результат: владелец отправляет сообщение через Telegram и получает реальный ответ модели из постоянно работающей выбранной среды. Границы платформы остаются под контролем владельца.
- состав: [`BR_001`](specifications/business_requirements.md#br_001), [`BR_004`](specifications/business_requirements.md#br_004), [`BR_005`](specifications/business_requirements.md#br_005), [`BR_006`](specifications/business_requirements.md#br_006), [`BR_033`](specifications/business_requirements.md#br_033), [`BR_036`](specifications/business_requirements.md#br_036), [`SYS_001`](specifications/system_specification.md#sys_001), [`SYS_002`](specifications/system_specification.md#sys_002), [`SYS_003`](specifications/system_specification.md#sys_003), [`SYS_004`](specifications/system_specification.md#sys_004), [`SYS_006`](specifications/system_specification.md#sys_006), [`SYS_020`](specifications/system_specification.md#sys_020), [`SYS_024`](specifications/system_specification.md#sys_024), [`SYS_027`](specifications/system_specification.md#sys_027), [`SEC_CTL_001`](specifications/system_specification.md#sec_ctl_001), [`SEC_CTL_002`](specifications/system_specification.md#sec_ctl_002), [`SEC_CTL_003`](specifications/system_specification.md#sec_ctl_003), [`SEC_CTL_005`](specifications/system_specification.md#sec_ctl_005), [`SEC_CTL_008`](specifications/system_specification.md#sec_ctl_008), [`SEC_CTL_020`](specifications/system_specification.md#sec_ctl_020), [`INF_REQ_001`](specifications/infrastructure_baseline.md#inf_req_001), [`INF_REQ_002`](specifications/infrastructure_baseline.md#inf_req_002), [`INF_REQ_003`](specifications/infrastructure_baseline.md#inf_req_003), [`INF_REQ_006`](specifications/infrastructure_baseline.md#inf_req_006), [`INF_REQ_010`](specifications/infrastructure_baseline.md#inf_req_010), [`INF_REQ_012`](specifications/infrastructure_baseline.md#inf_req_012), [`INF_REQ_013`](specifications/infrastructure_baseline.md#inf_req_013), [`INF_REQ_015`](specifications/infrastructure_baseline.md#inf_req_015), [`INF_REQ_016`](specifications/infrastructure_baseline.md#inf_req_016).
- ADR этого этапа: [`ADR_005`](adr/adr_005_first_model_provider_selection.md#adr_005), [`ADR_006`](adr/adr_006_agent_environment_framework.md#adr_006), [`ADR_007`](adr/adr_007_cloud_provider_selection.md#adr_007), [`ADR_009`](adr/adr_009_secret_management_strategy.md#adr_009).
- карта решений: [`ADR_005`](adr/adr_005_first_model_provider_selection.md#adr_005) → [`TASK_015`](work/tasks/task_015_real_model_provider.md), [`ADR_006`](adr/adr_006_agent_environment_framework.md#adr_006) → [`TASK_014`](work/tasks/task_014_real_runtime.md), [`ADR_007`](adr/adr_007_cloud_provider_selection.md#adr_007) и [`ADR_009`](adr/adr_009_secret_management_strategy.md#adr_009) → [`TASK_013`](work/tasks/task_013_inf_008.md).

### Обязательный пользовательский результат

До принятия этапа должен быть доказан один внешний сценарий: разрешённый владелец отправляет текст реальному Telegram-боту и получает ответ от реального поставщика модели в выбранной постоянно работающей среде. До вызова модели проверяются allowlist и аварийный выключатель; при обязательном VPN-профиле потеря туннеля не допускает вызова модели. Заглушка канала, RuntimePort или ModelGateway не является доказательством этого результата.

### Подэтапы

1. Сравнить 2–3 сильных варианта среды агента на одном минимальном сквозном сценарии.
   - При равном соответствии предпочитать зрелое решение с открытым исходным кодом.
   - Сравнить интерфейсы модели и инструментов, внешнюю границу контроля владельца, состояние и отмену, расширяемость, безопасность, сопровождение и сложность интеграции.
   - Прекратить сравнение, когда данных достаточно, и зафиксировать выбор в ADR.
2. Сравнить небольшой набор подходящих площадок размещения. Учитывать доступность, вычисления, сеть, секреты, резервное копирование, восстановление, стоимость, простоту эксплуатации и переносимость. Устойчивый выбор зафиксировать в ADR.
3. Развернуть минимально достаточную рабочую среду согласно выбранным решениям и `INF_REQ_*`.
4. Подключить одного поставщика модели через [`ARC_CMP_004`](specifications/architecture_baseline.md#arc_cmp_004) и проверить время ожидания, бюджет и обработку ошибок.
5. Реализовать минимальный сквозной сценарий Telegram по [`SYS_001`](specifications/system_specification.md#sys_001)–[`SYS_004`](specifications/system_specification.md#sys_004) и [`ARC_FLOW_001`](specifications/architecture_baseline.md#arc_flow_001) без повтора архитектурного контракта. Добавить только ограниченный независимый административный путь [`SYS_006`](specifications/system_specification.md#sys_006) для аварийного выключателя; это не включает общий CLI в продуктовый периметр V1.
6. Проверить внешний сценарий и отрицательные сценарии: чужая личность, аварийный выключатель, недоступная модель, секреты в журналах, обязательный сетевой путь и контролируемый перезапуск/повторное развёртывание минимального контура.

### Очередь, закрывающая пользовательский результат

[`TASK_012`](work/tasks/task_012_inf_007.md) и [`TASK_013`](work/tasks/task_013_inf_008.md) завершают наблюдаемость и управляемое развёртывание. Затем обязательны: [`TASK_014`](work/tasks/task_014_real_runtime.md) — выбранная среда агента, [`TASK_015`](work/tasks/task_015_real_model_provider.md) — реальный поставщик модели, [`TASK_016`](work/tasks/task_016_real_telegram.md) — реальный Telegram Bot API, [`TASK_017`](work/tasks/task_017_m02_live_e2e.md) — независимое сквозное доказательство. Компонентные TASK, использующие только stub-реализации, не могут заменить эти четыре результата.

Полное резервное копирование, восстановление ценного состояния, памяти и проектов по [`SYS_025`](specifications/system_specification.md#sys_025), [`SEC_CTL_013`](specifications/system_specification.md#sec_ctl_013) и [`INF_REQ_009`](specifications/infrastructure_baseline.md#inf_req_009)–[`INF_REQ_014`](specifications/infrastructure_baseline.md#inf_req_014) доказывается в [`m04`](#m04)/[`m06`](#m06). [`m02`](#m02) не подменяет это требование облегчённым smoke-тестом.

До перевода [`m02`](#m02) в `in-progress` создаётся профиль качества. Состав уже выражен точными идентификаторами. Принятие зависит от выполнения требований и доказательств, а не от названия выбранной технологии или поставщика.

<a id="m03"></a>
## m03 — Файлы, исследования и новостная аналитика

- work_state: `planned`
- результат: помощник отвечает по материалам пользователя и интернет-источникам с указанием происхождения данных. Он формирует полезный исследовательский и новостной поток без повторов.
- состав: [`BR_003`](specifications/business_requirements.md#br_003), [`BR_011`](specifications/business_requirements.md#br_011), [`BR_012`](specifications/business_requirements.md#br_012), [`BR_026`](specifications/business_requirements.md#br_026), [`BR_027`](specifications/business_requirements.md#br_027), [`BR_028`](specifications/business_requirements.md#br_028), [`SYS_008`](specifications/system_specification.md#sys_008), [`SYS_009`](specifications/system_specification.md#sys_009), [`SYS_010`](specifications/system_specification.md#sys_010), [`SYS_022`](specifications/system_specification.md#sys_022), [`SYS_023`](specifications/system_specification.md#sys_023), [`SEC_CTL_004`](specifications/system_specification.md#sec_ctl_004), [`SEC_CTL_007`](specifications/system_specification.md#sec_ctl_007), [`SEC_CTL_009`](specifications/system_specification.md#sec_ctl_009), [`SEC_CTL_010`](specifications/system_specification.md#sec_ctl_010), [`SEC_CTL_012`](specifications/system_specification.md#sec_ctl_012), [`INF_REQ_004`](specifications/infrastructure_baseline.md#inf_req_004), [`INF_REQ_005`](specifications/infrastructure_baseline.md#inf_req_005), [`INF_REQ_007`](specifications/infrastructure_baseline.md#inf_req_007).
- ADR этого этапа: нет.

### Подэтапы

1. Поддержать один реально нужный поток обработки файлов с указанием происхождения данных.
2. Ввести безопасную временную рабочую область и ограничения ресурсов.
3. Реализовать интернет-исследование с первоисточниками и явной неопределённостью.
4. Добавить объединение выводов, удаление повторов и персональный фильтр важности.
5. Получить положительные и отрицательные доказательства для границы недоверенного содержимого и ресурсных ограничений.

<a id="m04"></a>
## m04 — Память, проекты и переносимое состояние

- work_state: `planned`
- результат: система сохраняет полезный контекст между сессиями и формирует статус проектов, решений, обязательств, рисков и следующих действий.
- состав: [`BR_002`](specifications/business_requirements.md#br_002), [`BR_010`](specifications/business_requirements.md#br_010), [`BR_022`](specifications/business_requirements.md#br_022), [`BR_023`](specifications/business_requirements.md#br_023), [`BR_024`](specifications/business_requirements.md#br_024), [`SYS_010`](specifications/system_specification.md#sys_010), [`SYS_011`](specifications/system_specification.md#sys_011), [`SYS_012`](specifications/system_specification.md#sys_012), [`SYS_029`](specifications/system_specification.md#sys_029), [`SEC_CTL_006`](specifications/system_specification.md#sec_ctl_006), [`SEC_CTL_013`](specifications/system_specification.md#sec_ctl_013), [`SEC_CTL_019`](specifications/system_specification.md#sec_ctl_019), [`INF_REQ_008`](specifications/infrastructure_baseline.md#inf_req_008), [`INF_REQ_009`](specifications/infrastructure_baseline.md#inf_req_009), [`INF_REQ_014`](specifications/infrastructure_baseline.md#inf_req_014).
- ADR этого этапа: [`ADR_007`](adr/adr_007_cloud_provider_selection.md#adr_007), [`ADR_008`](adr/adr_008_data_storage_schema.md#adr_008).
- карта решений: [`ADR_007`](adr/adr_007_cloud_provider_selection.md#adr_007) назначен [`TASK_013`](work/tasks/task_013_inf_008.md); [`ADR_008`](adr/adr_008_data_storage_schema.md#adr_008) — назначить при декомпозиции до старта.

### Подэтапы

1. Ввести постоянную память с происхождением, уверенностью и областью данных.
2. Добавить исправление, удаление и выгрузку данных владельцем.
3. Сформировать контекст и состояние проектов.
4. Подключить постоянное хранилище без привязки прикладной модели к конкретной реализации.
5. Доказать резервное копирование, восстановление и проверку результата. Удалённая или исправленная запись не должна возвращаться как актуальная.

<a id="m05"></a>
## m05 — Плановые задачи и ежедневный брифинг

- work_state: `planned`
- результат: владелец может создавать и управлять разрешёнными однократными и регулярными задачами, которые надёжно выполняются по расписанию. Первый обязательный сценарий — единая приоритетная сводка без дублей и скрытого расширения полномочий.
- состав: [`BR_013`](specifications/business_requirements.md#br_013), [`BR_028`](specifications/business_requirements.md#br_028), [`BR_036`](specifications/business_requirements.md#br_036), [`SYS_013`](specifications/system_specification.md#sys_013), [`SYS_024`](specifications/system_specification.md#sys_024), [`SYS_030`](specifications/system_specification.md#sys_030), [`SEC_CTL_012`](specifications/system_specification.md#sec_ctl_012), [`SEC_CTL_017`](specifications/system_specification.md#sec_ctl_017), [`INF_REQ_001`](specifications/infrastructure_baseline.md#inf_req_001), [`INF_REQ_008`](specifications/infrastructure_baseline.md#inf_req_008).
- ADR этого этапа: нет.

### Подэтапы

1. Реализовать общий планировщик через обычный путь выполнения задачи и те же полномочия без отдельного привилегированного пути.
2. Поддержать создание, просмотр, изменение, приостановку, возобновление и удаление однократных и повторяющихся расписаний с явным часовым поясом и сохранением состояния между перезапусками.
3. Добавить наблюдаемое состояние следующего и последнего запуска, защиту от дублей, правила пропущенного запуска и отключения.
4. Собрать единую сводку и фильтрацию по важности как первый обязательный сценарий общего планировщика.
5. Проверить задержанный и повторный запуск, восстановление расписания после перезапуска и фактическое отключение. Перед каждым запуском повторно проверять полномочия и аварийный выключатель.

До перевода этого этапа в `in-progress` создаётся профиль качества с доказательствами для общего планировщика и сценария сводки. Состав уже выражен точными идентификаторами.

<a id="m06"></a>
## m06 — Стабилизация и приёмка V1

- work_state: `planned`
- результат: объединённый контур V1 пригоден для регулярного использования и восстанавливается после типовых отказов без ослабления контроля владельца.
- состав: [`BR_001`](specifications/business_requirements.md#br_001), [`BR_002`](specifications/business_requirements.md#br_002), [`BR_003`](specifications/business_requirements.md#br_003), [`BR_004`](specifications/business_requirements.md#br_004), [`BR_005`](specifications/business_requirements.md#br_005), [`BR_006`](specifications/business_requirements.md#br_006), [`BR_010`](specifications/business_requirements.md#br_010), [`BR_011`](specifications/business_requirements.md#br_011), [`BR_012`](specifications/business_requirements.md#br_012), [`BR_013`](specifications/business_requirements.md#br_013), [`BR_022`](specifications/business_requirements.md#br_022), [`BR_023`](specifications/business_requirements.md#br_023), [`BR_024`](specifications/business_requirements.mv�_6����k�w��}��-�-]�]�����]-�����-����m���-����}]�2ࠣ2���	-��Mm�򢣢	�]]B�]]]�M��M��m���-���-]]��-R�]M=��-���	]���]M=��-���R-�����]����]]]�B����=]-�ࠣB���	�]-�}--��-¢��
M������R�-������]�}�]��]���6���WFVB�6�6V��VB�&V�V7FVB�ࠣR���
�M�-]����R�-����򢣢	]��=���-���]]"�M�-]�������]�-]"�-���-���-�2���]]]�B�-�����M�}]�]�=���-��RM��m]��=��-�����-]�-��-��M�-]��ࠢ22��	���]��-�����Rm]��] ��222
m]����	�������R}-]�]��R}M}��� �D4������VB �(i"���&�w&W72�=]�"�}��-2��(i"6���WFVB�=]�"}-]����-2�-R��-]���������R}-��"�"]�]������-�2(	B��66WF�6R��B�� ��222
m]���#�	}M}��}�����-� �� �D4������VB �(i"���&�w&W72�=]�"�}��-2��(i"&��6�VB���=m]�}-����-�(i"���&�w&W72�}-����-�}]�]���(i"6���WFVB��-}-]�]��� ��222
m]���3�����-��E"��}�]�Р� �E%��66WFVB�]�]��R�������-␢(i"7WW'6VFVB���-�R]�]��R}�]����-�R�E%��� ��222
m]���C�
-]"��}�]�Р� �DU5E��7W'&V�B��]�M���-]"��(i"7WW'6VFVB���-��-]"�DU5E��c"��=}�R�����]R�� ��22��	����m�}�]����m�����]�����	M��=M=��R6�����F��������}=]-��M����]M�--]����-à��FW�@�6�F�FFR(i"���&Wf�Wr(i"�&FV��r(i"&�&F���(i"66WFVB(i"&WF�&V@� ��	M�66WFVF��M�M"��m]"�]]�-�"&V�V7FVF�	�r&WF�&VF�&V�V7FVF����=�-�}--�]#���-�]��R�����--���R�]M��m]��R�}M"��-=�-]��"6�F�FFV࠭	���R=��-���]]]�M�#�������&Wf�Wv����]�mM]��R��}�}]��R�}-����-��-�M]�]b�}-]-������&FV��v�������M�m��-�����-]���������=m�-��=�]��S���&�&F����-]��}M����-����-����]�]����=��}]���-�"��-]]Ӱ��66WFVF���}-]����RWf�FV�6R�-���-��-�}���24��]��2-]�����&WF�&VF���=-�}m���-���}]���-�-��R�������}���-�}-���}-����-���-]]��࠭
�]m�M�}��R����M��}-]��--�R��--���-�}M]âM��6��������]�M�-�"�6�����ƖfV7�6�R��F҂������6�F�FFW2�6�����ƖfV7�6�R��B��M��F���(	B"�F����ƖfV7�6�R��F҂������6�F�FFW2�F����ƖfV7�6�R��B��