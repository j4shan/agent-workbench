---
name: visualize_with_drawio
description: Create or revise a visualization with the draw.io app from a written specification. Use when the user asks for a diagram, flowchart, architecture diagram, schematic, or other draw.io visualization.
disable-model-invocation: true
---

# Visualize with draw.io

| Reference | Link |
| --- | --- |
| draw.io editor and shape libraries | [jgraph/drawio](https://github.com/jgraph/drawio) |
| draw.io desktop app and command line | [jgraph/drawio-desktop](https://github.com/jgraph/drawio-desktop) |
| draw.io XML | [XML reference](https://raw.githubusercontent.com/jgraph/drawio-mcp/main/shared/xml-reference.md) |
| draw.io styles | [Style reference](https://raw.githubusercontent.com/jgraph/drawio-mcp/main/shared/style-reference.md) |
| Mermaid in draw.io | [Mermaid reference](https://raw.githubusercontent.com/jgraph/drawio-mcp/main/shared/mermaid-reference.md) |

**Objective.** Create a draw.io visualization from a written specification so the source can be checked against the intended result.

**Your tasks.** Write the specification, create the visualization with the draw.io app, verify the source against the specification, and export a PNG when requested.

## 1. Write the specification

Create `resources/img_prompt/<name>_spec.md`. Create the directory when it is missing.

Default to a light theme unless the user requests another theme.

## 2. Create the visualization

Use the draw.io app to create `resources/img/<name>.drawio`. Create the directory when it is missing.

## 3. Verify the source

Verify `resources/img/<name>.drawio` against `resources/img_prompt/<name>_spec.md`. Revise the visualization in the draw.io app until it matches the specification.

## 4. Export the PNG

When the user requests a PNG, export `resources/img/<name>.PNG` from the verified draw.io source.
