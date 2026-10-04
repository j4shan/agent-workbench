---
name: documentation-writer
description: Write or revise project README files, design specifications, and other human-facing documentation after an implementation or design change. Use when finalized technical changes need clear English documentation; exclude inline code comments and docstrings.
---

# Documentation writer

## Objective

Produce accurate project documentation in clear, natural English from a distilled account of the
final implementation. Optimize information order, sentence structure, terminology, and word choice
without importing abandoned approaches or debugging history.

Your tasks are to distill the final state, prepare a bounded evidence manifest, and invoke the
documentation writer.

## 1. Distill the final state

Create a documentation brief after implementation and validation are complete. Include only facts
that describe the resulting system. Exclude intermediary discussion, rejected designs, failed
experiments, and raw command output unless a lasting diagnostic behavior belongs in the docs.

Set these fields:

- `workspace_root`: the absolute project root.
- `objective`: the specific documentation outcome.
- `target_documents`: project-relative paths to the human-facing files the writer may edit.
- `finalized_changes`: completed behavior and decisions.
- `changed_components`: objects with `component`, `summary`, and `reader_impact`.
- `audience`: the intended readers.
- `desired_reader_outcome`: what readers should understand or be able to do.
- `constraints`: required terminology and scope limits.
- `validation`: documentation checks the writer may run.
- `uncertainties`: unresolved facts the writer must not silently invent.
- `allow_create`: whether missing target documents may be created.

## 2. Build the evidence manifest

Add an `evidence_manifest` entry for every file that may be needed to verify or expand the
distilled facts. Give each entry an absolute `path`, a short `relevance` explanation, and a `facts`
list. Include source, configuration, tests, or existing documentation only when it supports the
final state.

Keep the manifest selective. Never substitute an unfocused repository scan for a useful manifest.
Every evidence path must exist inside `workspace_root`.

## 3. Invoke the writer

Save the brief as temporary JSON outside the project, then run:

```bash
python3 .agents/skills/documentation-writer/scripts/write_documentation.py --brief /absolute/path/to/brief.json
```

Pass `--brief -` to read JSON from standard input. Pass `--validate-only` before delegation when the
brief was assembled mechanically or its boundaries are uncertain.

The launcher uses Codex with `gpt-6-sol` and medium reasoning. It permits edits only to
`target_documents` and fails if the run changes another project file. Review the reported changed
documents and unresolved uncertainties, then remove the temporary brief.

## 4. Keep code documentation out of scope

Never use this skill to write inline comments, docstrings, or generated API annotations. Handle
those as code edits in the primary implementation task.
