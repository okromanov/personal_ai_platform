---
name: architecture-scheme
description: Create or update the personal_ai_platform architecture infographic and its editable SVG source when the user asks to change the project scheme, entity hierarchy, labels, or visual architecture map.
---

# Architecture Scheme

Maintain the repository's architecture infographic as an editable, evidence-based SVG.

Treat the current SVG as the design baseline. Make the smallest layout change that satisfies the request; do not rebuild, restyle, simplify, or replace the existing composition unless the user explicitly asks for a redesign.

## Repository context

Before editing, read `AGENTS.md`, `project_status.md`, and the relevant parts of:

- `project_rules.md`
- `specifications/architecture_baseline.md`
- `operations/change_process.md`

Treat those files as sources for established project components and security boundaries. Do not change authority documents merely to make the diagram consistent unless the user explicitly requests that broader change.

## Canonical artifact set

Keep these files synchronized:

- `work/artefacts/personal_ai_platform_architecture.svg` — editable source and canonical visual
- `work/artefacts/personal_ai_platform_architecture.png` — rendered preview
- `work/artefacts/personal_ai_platform_architecture_source.json` — hierarchy, palette, and section metadata

Do not use generated raster imagery to replace the SVG. Preserve editable shapes, text, connectors, and semantic grouping.

## Entity hierarchy

For this infographic, preserve the declared project hierarchy:

`Capability → Skill → Tool → Implementation`

- A Capability represents a stable owner need and can group several Skills.
- A Skill is a reusable workflow and routes execution through the appropriate Tool.
- Skills can be reused across agents and workflows.
- A Tool is an authorized atomic operation.
- An Implementation is a replaceable API, MCP server, library, provider, or adapter.
- Implementation details do not become the contract of a Capability or Skill.

## Editing workflow

1. Inspect the current SVG and source JSON before changing labels, relationships, or layout.
2. Preserve the existing canvas structure, typography, palette, ARC/INF identifiers, layer numbering, owner-control plane, emergency switch priority, RuntimePort boundary, gateways, quality checks, feedback rails, and infrastructure layer unless the requested change explicitly supersedes them.
3. Keep the hierarchy visually legible as a directional flow. When one Capability groups several Skills, show the cardinality or branching explicitly.
4. Update the source JSON whenever hierarchy, palette, canvas, or section names change.
5. Render the SVG with Inkscape:

   ```bash
   inkscape work/artefacts/personal_ai_platform_architecture.svg \
     --export-filename=work/artefacts/personal_ai_platform_architecture.png \
     --export-width=1600
   ```

6. Inspect the full-resolution PNG. Check for clipped text, missing glyphs, overlapping connectors, low contrast, and inconsistent spacing.
7. Validate that the SVG is well-formed XML and the source JSON parses successfully.
8. Publish changes through a repository branch and pull request; do not write directly to `main`.

## Visual constraints

- Use a light neutral background, dark navy orchestration core, and distinct semantic colors for Capability, Skill, Tool, Implementation, and owner control.
- Prefer concise labels and short annotations over dense paragraphs.
- Keep security invariants adjacent to the relevant gateway or control boundary.
- Preserve a coherent reading order from owner input through orchestration and authorized execution.
