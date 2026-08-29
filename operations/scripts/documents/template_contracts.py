from __future__ import annotations

import ast
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
CODEOWNERS_PATH = Path(".github/CODEOWNERS")
_MARKDOWN_FENCE = re.compile(r"(?ms)^\x60\x60\x60markdown\s*$\n(.*?)^\x60\x60\x60\s*$")
_TOKEN = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")
_CONTRACT_API = frozenset({"assert_registered_output", "render_contract"})


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


def _codeowner_patterns(root: Path, owner: str) -> list[str]:
    path = root / CODEOWNERS_PATH
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    patterns: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) >= 2 and owner in fields[1:]:
            patterns.append(fields[0])
    return patterns


def _codeowner_pattern_matches(path: str, pattern: str) -> bool:
    normalized = pattern.removeprefix("/")
    if normalized.endswith("/"):
        return path.startswith(normalized)
    return fnmatch.fnmatchcase(path, normalized)


def _generator_uses_contract_api(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError):
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        name = function.id if isinstance(function, ast.Name) else None
        if isinstance(function, ast.Attribute):
            name = function.attr
        if name in _CONTRACT_API:
            return True
    return False


def _output_matches(path: str, pattern: str) -> bool:
    """Match one path segment at a time so `*` cannot cross directories."""
    path_parts = Path(path).parts
    pattern_parts = Path(pattern).parts
    return len(path_parts) == len(pattern_parts) and all(
        fnmatch.fnmatchcase(value, expected)
        for value, expected in zip(path_parts, pattern_parts, strict=True)
    )


def validate_template_registry(root: Path) -> list[str]:
    errors: list[str] = []
    try:
        registry = load_template_registry(root)
    except TemplateContractError as exc:
        return [str(exc)]

    owner = registry.get("required_owner")
    if not isinstance(owner, str) or not owner.startswith("@"):
        errors.append("required_owner должен содержать GitHub owner вида @login")
        owner = ""
    protected_paths = registry.get("protected_paths")
    if not isinstance(protected_paths, list) or any(
        not isinstance(value, str) or not value for value in protected_paths
    ):
        errors.append("protected_paths должен быть списком непустых строк")
        protected_paths = []
    enforcement_tests = registry.get("enforcement_tests")
    if not isinstance(enforcement_tests, list) or any(
        not isinstance(value, str) or not value for value in enforcement_tests
    ):
        errors.append("enforcement_tests должен быть списком непустых строк")
        enforcement_tests = []

    contracts = registry["contracts"]
    assert isinstance(contracts, dict)
    registered_templates: set[str] = set()
    registered_generators: set[str] = set()
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
                generator_path = str(generator)
                registered_generators.add(generator_path)
                if not (root / generator_path).is_file():
                    errors.append(f"{contract_id}: отсутствует generator {generator_path}")
                elif not _generator_uses_contract_api(root / generator_path):
                    errors.append(f"{contract_id}: generator {generator_path} обходит contract API")

    actual_templates = {
        path.relative_to(root).as_posix() for path in (root / TEMPLATE_DIRECTORY).glob("*.md")
    }
    for template in sorted(actual_templates - registered_templates):
        errors.append(f"Шаблон не зарегистрирован: {template}")
    for template in sorted(registered_templates - actual_templates):
        errors.append(f"В реестре указан отсутствующий шаблон: {template}")

    protected = {
        *[str(value) for value in protected_paths],
        *[str(value) for value in enforcement_tests],
        *registered_templates,
        *registered_generators,
    }
    patterns = _codeowner_patterns(root, owner) if owner else []
    for path in sorted(protected):
        if not (root / path).is_file():
            errors.append(f"Защищённый путь отсутствует: {path}")
        if not any(_codeowner_pattern_matches(path, pattern) for pattern in patterns):
            errors.append(f"CODEOWNERS не защищает {path} владельцем {owner or '<invalid>'}")
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
    raw_outputs = contract.get("outputs", [])
    outputs = raw_outputs if isinstance(raw_outputs, list) else []
    patterns = [str(value) for value in outputs]
    if not any(_output_matches(relative, pattern) for pattern in patterns):
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
