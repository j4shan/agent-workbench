---
name: documentation-writer
description: Delegate writing or revising human-facing project documentation to a Codex subagent for clear, readable prose. Use when the user asks to have Codex write, rewrite, polish, or update documentation, including READMEs, guides, and design specifications. Exclude inline code comments, docstrings, and generated API documentation.
---

# Documentation writer

## Objective

Delegate human-facing documentation updates to a Codex subagent to use GPT's strength in clear,
readable prose.

## Your tasks

Prepare the context, invoke Codex, and review the resulting documentation. Apply this workflow when
the user asks for documentation delegation to Codex. Never trigger it solely because code changed.

## 1. Prepare the context

Scope the request to human-facing project documentation, such as READMEs, guides, design
specifications, and explanations. Never delegate inline code comments, docstrings, or generated API
documentation through this skill.

State the goal and the project-relative target documents. Include the audience, relevant facts,
evidence paths, constraints, and unresolved questions when they help the writer. For implementation
updates, describe the final state; omit abandoned approaches and debugging history. For design
documentation, distinguish agreed decisions from proposals and open questions. Do not require a
completed implementation for a standalone writing or revision task.

Use a plain-language request by default. When a consistent format helps repeated calls, use the
optional [annotated JSON Schema](references/brief.schema.json). Use it for the request context, not
as the CLI's `--output-schema`, which controls the final response. Do not require JSON or a schema
validator to delegate a writing task.

Keep evidence selective. Resolve target and evidence paths within the project. Create missing
target documents when the request authorizes creation; otherwise update existing documents only.

## 2. Invoke Codex

Save a temporary request file outside the project. Start it with these writing instructions, then
append the task context as plain text or JSON:

```text
Write or revise the named project documents in clear, natural English for the stated audience.
Improve information order, sentence structure, terminology, and word choice.

Edit only the named target documents. Create a missing target only when the request authorizes it.
Never edit source code, tests, configuration, inline comments, docstrings, or generated API docs.
Preserve established terminology, useful content, and document structure unless the task calls
for changing them. Use direct sentences and concrete terms; remove repetition and filler.
Consult the supplied evidence as needed. Do not perform an unfocused repository scan or invent
behavior. Distinguish agreed decisions from proposals and report unresolved uncertainty.
Run only relevant documentation checks supplied in the request.
Finish by reporting changed documents, what you clarified, and any remaining uncertainty.

Task context:
```

Run from the project root, replacing the request-file path with the file you created:

```bash
codex exec --ephemeral --ignore-user-config \
  --sandbox workspace-write --model gpt-6-sol \
  --config 'model_reasoning_effort="medium"' \
  --cd "$PWD" - < "/absolute/path/to/documentation-request.txt"
```

Use the requested model or reasoning effort when the user specifies either. If `codex` is not on
`PATH`, locate an installed executable before invoking it.

## 3. Review the result

Note existing workspace changes before delegation. Afterward, compare the diff and new files with
that starting state. Check the prose, factual accuracy, requested scope, and reported uncertainty.
Review changes outside the named documents as scope violations; do not discard unrelated work.
Treat a failed CLI invocation as incomplete work and inspect any partial edits before retrying.

Review scope yourself; the workspace sandbox does not restrict edits to individual target files.
Report the documentation changes and unresolved questions, then remove the temporary request file.
