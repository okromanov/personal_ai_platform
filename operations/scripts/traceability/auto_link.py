"""Автоматическое заполнение связей трассировки между документами требований."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def _extract_id_field(text: str, field_name: str) -> list[str]:
    """Extract list value from YAML field."""
    pattern = rf"^{re.escape(field_name)}:\s*\n((?:  - .*\n)*)"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return []

    items = re.findall(r"  - (.+)", match.group(1))
    return items


def _update_yaml_field(text: str, field_name: str, values: list[str]) -> str:
    """Update or create YAML field with list of values."""
    if not values:
        return text

    # Remove existing field if present
    pattern = rf"^{re.escape(field_name)}:\s*\n((?:  - .*\n)*)"
    text = re.sub(pattern, "", text, flags=re.MULTILINE)

    # Find end of metadata
    metadata_end = text.find("\n---\n") + 1
    if metadata_end == 0:
        metadata_end = text.find("\n---") + 1

    # Insert new field before end of metadata
    field_content = f"{field_name}:\n" + "\n".join(f"  - {v}" for v in sorted(set(values))) + "\n"

    return text[:metadata_end] + field_content + text[metadata_end:]


def _extract_requirement_definitions(root: Path) -> dict[str, dict[str, Any]]:
    """Extract all requirement IDs and their metadata."""
    requirements = {}

    spec_files = {
        "BR": root / "specifications" / "business_requirements.md",
        "SYS": root / "specifications" / "system_specification.md",
        "SEC_CTL": root / "specifications" / "threat_model.md",
        "ARC": root / "specifications" / "architecture_baseline.md",
        "INF_REQ": root / "specifications" / "infrastructure_baseline.md",
    }

    for req_type, spec_file in spec_files.items():
        if not spec_file.exists():
            continue

        content = spec_file.read_text(encoding="utf-8")

        # Find all IDs of this type
        if req_type == "BR":
            pattern = r"<a id=\"br_(\d+)\"></a>"
        elif req_type == "SYS":
            pattern = r"<a id=\"sys_(\d+)\"></a>"
        elif req_type == "SEC_CTL":
            pattern = r"<a id=\"sec_ctl_(\d+)\"></a>"
        elif req_type == "ARC":
            pattern = r"<a id=\"arc_(\d+)\"></a>"
        else:  # INF_REQ
            pattern = r"<a id=\"inf_req_(\d+)\"></a>"

        for match in re.finditer(pattern, content, re.IGNORECASE):
            req_id = f"{req_type}_{int(match.group(1)):03d}"
            requirements[req_id] = {
                "type": req_type,
                "file": spec_file,
                "position": match.start(),
            }

    return requirements


def _find_traces_to_relationships(root: Path, requirements: dict) -> dict[str, list[str]]:
    """Find traces_to relationships from specifications."""
    traces: dict[str, list[str]] = {}

    # Rules for finding traces
    # SYS -> ARC (system requirements implemented by architecture)
    # BR -> SYS (business requirements covered by system requirements)
    # SEC_CTL -> ARC (security controls implemented by architecture)

    arc_file = root / "specifications" / "architecture_baseline.md"

    if arc_file.exists():
        arc_content = arc_file.read_text(encoding="utf-8")
        # Look for "implements: [SYS_XXX]" patterns
        for match in re.finditer(r"implements?:\s*\n((?:  - [A-Z_0-9]+\n)*)", arc_content):
            for impl in re.findall(r"  - ([A-Z_0-9]+)", match.group(1)):
                if impl in requirements:
                    arc_id = re.search(
                        r"<a id=\"arc_(\d+)\"></a>.*?^### ARC_(\d+)",
                        arc_content[max(0, match.start() - 500) : match.start()],
                        re.MULTILINE | re.DOTALL,
                    )
                    if arc_id:
                        arc_num = f"ARC_{int(arc_id.group(2)):03d}"
                        traces.setdefault(impl, []).append(arc_num)

    return traces


def auto_link_requirements(root: Path) -> dict[str, list[str]]:
    """Analyze specifications and generate trace relationships."""
    requirements = _extract_requirement_definitions(root)
    traces = _find_traces_to_relationships(root, requirements)

    return traces


if __name__ == "__main__":
    root = Path.cwd()
    # Find project root
    while root.parent != root:
        if (root / "project_rules.md").exists():
            break
        root = root.parent

    traces = auto_link_requirements(root)
    if traces:
        print("Найдены связи трассировки:")
        for req_id, linked_ids in sorted(traces.items()):
            print(f"  {req_id} → {', '.join(sorted(linked_ids))}")
    else:
        print("Связи трассировки не найдены.")
