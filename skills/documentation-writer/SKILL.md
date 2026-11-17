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

Retrieve the general `content-writer` role from its user-owned configuration. Each role file is
`["model", "reasoning-effort"]`. Read one snapshot so an atomic update cannot mix the two values.
Run this complete command from the project root, substituting the request file you created:

```bash
role_dir="${SUBAGENT_MODELS_DIR-$HOME/Library/Application Support/subagent-models}"
case "$role_dir" in /*) ;; *) printf 'Configuration directory must be absolute\n' >&2; exit 1 ;; esac
role_config="$(/usr/bin/plutil -convert json -o - "$role_dir/content-writer.json")" || exit 1
array_length="$(/usr/bin/plutil -extract settings raw -expect array -o - - <<< "{\"settings\":$role_config}")" || exit 1
[[ "$array_length" == 2 ]] || { printf 'Expected exactly two role settings\n' >&2; exit 1; }
model="$(/usr/bin/plutil -extract 0 raw -expect string -o - - <<< "$role_config")" || exit 1
effort="$(/usr/bin/plutil -extract 1 raw -expect string -o - - <<< "$role_config")" || exit 1
"$HOME/.local/bin/gpt-exec" \
  --model "$model" --reasoning-effort "$effort" \
  --sandbox workspace-write --project "$PWD" \
  --prompt-file "/absolute/path/to/documentation-request.txt"
```

If the user explicitly requests a model or effort for this call, replace only that local variable
before invoking `gpt-exec`. Do not update stored preferences. Never pin a model version in this skill
or substitute a fallback. When configuration or the installed command is missing, report the setup
needed; do not create machine configuration or install tools as part of a writing request. If Codex
is not on `PATH`, locate an installed executable and add its directory for the invocation.

Let `gpt-exec` redirect stdin from the finite request file and preserve Codex's status. Keep background
scheduling, monitoring, and cancellation with the calling process runner. A launched process is not
a completed writing task.

## 3. Review the result

Note existing workspace changes before delegation. Afterward, compare the diff and new files with
that starting state. Check the prose, factual accuracy, requested scope, and reported uncertainty.
Review changes outside the named documents as scope violations; do not discard unrelated work.
Treat a failed CLI invocation as incomplete work and inspect any partial edits before retrying.

Review scope yourself; the workspace sandbox does not restrict edits to individual target files.
Report the documentation changes and unresolved questions, then remove the temporary request file.
