from __future__ import annotations

import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import find_project_root, read_text

REGISTRY_PATH = Path("operations/template_registry.json")
TEMPLATE_DIRECTORY = Path("operations/templates")
_MARKDOWN_FENCE = re.compile(r"(?ms)^\x60\x60\x60markdown\s*$\n(.*?)^\x60\x60\x60\s*$")
_TOKEN = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")


class TemplateContractError(ValueError):
    pass


def load_template_registry(root: Path) -> dict[str, object]:
    path = root / REGISTRY_PATH
    try:
        data = json.loads(read_text(path))
    except (OSError, json.JSONDecodeError) as exc:
        raise TemplateContractError(f"Некорректный реестр шаблонов {REGISTRY_PATH}: {exc}") from exc
    if data.get("version") != 1 or not isinstance(data.get("contracts"), dict):
        raise TemplateContractError("Реестр шаблонов должен иметь version=1 и contracts")
    return data


def validate_template_registry(root: Path) -> list[str]:
    errors: list[str] = []
    try:
        registry = load_template_registry(root)
    except TemplateContractError as exc:
        return [str(exc)]

    contracts = registry["contracts"]
    assert isinstance(contracts, dict)
    registered_templates: set[str] = set()
    for contract_id, raw in contracts.items():
        if not isinstance(raw, dict):
            errors.append(f"{contract_id}: контракт должен быть object")
            continue
        template = str(raw.get("template", ""))
        if not template.startswith(f"{TEMPLATE_DIRECTORY.as_posix()}/"):
            errors.append(f"{contract_id}: template должен находиться в operations/templates/")
        elif not (root / template).is_file():
            errors.append(f"{contract_id}: отсутствует шаблон {template}")
        elif template in registered_templates:
            errors.append(f"{contract_id}: шаблон {template} зарегистрирован повторно")
        registered_templates.add(template)
        outputs = raw.get("outputs")
        if not isinstance(outputs, list) or any(not str(value).strip() for value in outputs):
            errors.append(f"{contract_id}: outputs должен быть списком непустых строк")
        generators = raw.get("generators")
        if not isinstance(generators, list):
            errors.append(f"{contract_id}: generators должен быть списком")
        else:
            for generator in generators:
                if not (root / str(generator)).is_file():
                    errors.append(f"{contract_id}: отсутствует generator {generator}")

    actual_templates = {
        path.relative_to(root).as_posix() for path in (root / TEMPLATE_DIRECTORY).glob("*.md")
    }
    for template in sorted(actual_templates - registered_templates):
        errors.append(f"Шаблон не зарегистрирован: {template}")
    for template in sorted(registered_templates - actual_templates):
        errors.append(f"В реестре указан отсутствующий шаблон: {template}")
    return errors


def _contract(root: Path, contract_id: str) -> dict[str, object]:
    registry = load_template_registry(root)
    contracts = registry["contracts"]
    assert isinstance(contracts, dict)
    raw = contracts.get(contract_id)
    if not isinstance(raw, dict):
        raise TemplateContractError(f"Неизвестный шаблонный контракт: {contract_id}")
    return raw


def render_contract(
    root: Path,
    contract_id: str,
    values: Mapping[str, object],
) -> str:
    contract = _contract(root, contract_id)
    path = root / str(contract["template"])
    source = read_text(path)
    match = _MARKDOWN_FENCE.search(source)
    if match is None:
        raise TemplateContractError(f"{path.relative_to(root)}: отсутствует блок ```markdown")
    body = match.group(1)
    required = set(_TOKEN.findall(body))
    missing = sorted(required - set(values))
    if missing:
        raise TemplateContractError(
            f"{contract_id}: не переданы значения шаблона: {', '.join(missing)}"
        )
    rendered = _TOKEN.sub(lambda token: str(values[token.group(1)]), body)
    leftovers = sorted(set(_TOKEN.findall(rendered)))
    if leftovers:
        raise TemplateContractError(
            f"{contract_id}: после рендера остались токены: {', '.join(leftovers)}"
        )
    return rendered.rstrip() + "\n"


def assert_registered_output(root: Path, contract_id: str, output: Path) -> None:
    contract = _contract(root, contract_id)
    relative = output.resolve().relative_to(root.resolve()).as_posix()
    patterns = [str(value) for value in contract.get("outputs", [])]
    if not any(fnmatch.fnmatchcase(relative, pattern) for pattern in patterns):
        raise TemplateContractError(f"{contract_id}: путь {relative} не разрешён реестром шаблонов")


def main() -> int:
    root = find_project_root(Path.cwd())
    errors = validate_template_registry(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Template registry: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
