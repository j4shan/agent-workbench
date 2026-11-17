# Subagent model selection on macOS

Approved design, revised to use compact JSON arrays. Repository tools and skill adoption implement
this design; installation and creation of actual user preferences are separate explicit actions.

## Responsibilities

| Component | Responsibility |
| --- | --- |
| User configuration | Map each delegation role to a model and reasoning effort. |
| macOS `plutil` | Read a known role file directly for shell callers. |
| `subagent-model-upsert` | Create or update role configuration safely. |
| `gpt-exec` | Invoke Codex with explicit settings and finite prompt-file input. |
| Calling skill | Choose the role, retrieve settings, write the complete request, select permissions, compose the invocation, and assess the result. |

There is no standalone delegation skill. Model choices are not published as environment variables.
Each delegation reads configuration afresh, without scanning directories or searching file contents.

## Paths

| Source or destination | Purpose |
| --- | --- |
| `tools/subagent-model-upsert.sh` | Source for the configuration upsert command. |
| `tools/gpt-exec.sh` | Source for the invocation command. |
| `tools/install-tools.sh` | Explicit user-level tool installer, separate from skill installation. |
| `tools/tests/` | Tests with temporary configuration and a stub Codex executable. |
| `skills/execution-planning/scripts/review.py` | Bundled reviewer configuration and invocation functions, with a short CLI. |
| `~/.local/bin/subagent-model-upsert` | Installed configuration command. |
| `~/.local/bin/gpt-exec` | Installed invocation command. |
| `~/Library/Application Support/subagent-models/<role>.json` | User-owned configuration, one file per role. |

The installer copies executables only. Role configuration is created by a separate explicit upsert.
Existing skill installation keeps its current behavior. Installed commands can be called by their
absolute paths so GUI clients need no shell startup changes.

## Structured configuration

A role is a task-purpose name such as `content-writer` or `code-reviewer`. Use lowercase kebab-case
role names. Each file contains exactly two nonempty strings in a fixed order:

```json
["gpt-6.1-sol","high"]
```

| Index | Type | Meaning |
| --- | --- | --- |
| `0` | String | Explicit model ID passed to the runtime. |
| `1` | String | Explicit reasoning effort passed to the runtime. |

The upsert tool validates both identifiers and rejects extra or missing elements. Model IDs use
letters, digits, dots, underscores, colons, slashes, and hyphens; the first character is alphanumeric.
Effort values start with a lowercase letter and contain lowercase letters, digits, or hyphens.
Native `plutil` reads JSON arrays directly; no extra parser or schema version is needed for this
fixed pair.

The requested writer selection is GPT-6.1 Sol with high reasoning. The proposed initial reviewer
selection is the same, stored independently. This model ID and effort are listed in the
[official model catalog](https://developers.openai.com/api/docs/models).

Keep API credentials out of these files. Model availability and model-specific effort support are
validated by the runtime; a rejection does not trigger a fallback.

## Direct retrieval

The calling skill uses a known role path. Read a snapshot once, then extract both fields from that
snapshot so a concurrent atomic upsert cannot mix settings from different file versions:

```bash
role_dir="${SUBAGENT_MODELS_DIR-$HOME/Library/Application Support/subagent-models}"
case "$role_dir" in /*) ;; *) printf 'Configuration directory must be absolute\n' >&2; exit 1 ;; esac
role_config="$(/usr/bin/plutil -convert json -o - "$role_dir/content-writer.json")" || exit 1
array_length="$(/usr/bin/plutil -extract settings raw -expect array -o - - <<< "{\"settings\":$role_config}")" || exit 1
[[ "$array_length" == 2 ]] || { printf 'Expected exactly two role settings\n' >&2; exit 1; }
model="$(/usr/bin/plutil -extract 0 raw -expect string -o - - <<< "$role_config")" || exit 1
effort="$(/usr/bin/plutil -extract 1 raw -expect string -o - - <<< "$role_config")" || exit 1
```

`SUBAGENT_MODELS_DIR` is an optional directory override, useful for tests and alternate user
locations. It must be a nonempty absolute path. It does not export model settings. Never source a
configuration file as shell code. The wrapper validates both values before launching Codex.

An explicit user instruction for a particular delegation overrides the corresponding retrieved
field for that call. It does not update stored preferences. Missing, malformed, or incomplete
configuration stops delegation with a setup error; it never selects a hidden default.

## Robust upsert

Command:

```bash
"$HOME/.local/bin/subagent-model-upsert" \
  --role content-writer --model gpt-6.1-sol --reasoning-effort high
```

On creation, require both settings. On update, replace only the supplied array element and preserve
the other value. Validate the role name, exact two-string shape, identifier syntax, and arguments.
Reject malformed existing files rather than replacing them with defaults.

Use native macOS tools and Bash 3.2-compatible shell code. Create the configuration directory with
user-only access and role files with mode `600`. Serialize writers with a per-role atomic directory
lock and a bounded wait (10 seconds by default; `--lock-timeout` accepts 0 through 60 seconds).
On a lock timeout, report the lock; never silently remove another writer's lock. Prepare and validate a temporary JSON file in the destination directory, then rename it over the
role file. Readers see either the old or new complete file. Cleanup removes only this process's
temporary files and acquired lock. A failure leaves the existing role file intact.

## Reliable invocation

The skill supplies the complete invocation, including the settings it retrieved:

```bash
"$HOME/.local/bin/gpt-exec" \
  --prompt-file "$request_file" \
  --model "$model" --reasoning-effort "$effort" \
  --sandbox read-only --project "$PWD"
```

The wrapper requires all five options above. The prompt must be a readable, nonempty regular file,
not a terminal or FIFO. Support `read-only` and `workspace-write` sandboxes. Optional `--json` and
`--output-last-message` options support machine-readable progress and a final response artifact.

The wrapper validates inputs, builds an argument array, and replaces itself with `codex exec` using
the supplied model, effort, sandbox, and project. Its final prompt argument is `-`, and stdin is
explicitly redirected from the request file. It does not inherit the caller's open stdin pipe or
accept a second positional prompt. It uses no `eval` and performs no model selection of its own.
Authentication remains with Codex. Use ephemeral sessions and pass model and effort explicitly;
retain the user's other Codex configuration.

This addresses the reported EOF wait. Codex supports prompts from stdin and appending piped input
to a positional prompt, as described in the
[official non-interactive guide](https://learn.chatgpt.com/docs/non-interactive-mode#advanced-stdin-piping).

The wrapper stays in the foreground and preserves the child's exit status and signal behavior.
The caller's process runner owns scheduling, monitoring, deadlines, and cancellation. A launched
process is not proof that model work has started or completed. Record invocation metadata without
logging the prompt or secrets; use runtime progress and its terminal result to assess execution.
Finite stdin fixes this input wait, not every possible authentication, network, or runtime delay.
Failures are reported without automatic retries; the caller inspects partial edits before retrying.

## First adopters

| Skill | Role | Behavior |
| --- | --- | --- |
| `documentation-writer` | `content-writer` | Retrieve settings, preserve its documentation-only request scope, and invoke the shared command with `workspace-write`. Remove its hardcoded model and effort. |
| `execution-planning` | `code-reviewer` | Include a final review after implementation and verification for plans that change code, configuration, or executable helpers. Execute it with `read-only` permissions only when execution is authorized. |

Each skill owns its retrieval and invocation without depending on another skill being loaded.
The documentation writer uses native `plutil`. The planning skill bundles `load_review_settings()`
and `exec_review()` in `scripts/review.py`: the first reads one JSON snapshot through Python's
standard library, and the second replaces the process with shared `gpt-exec` in read-only mode.
Per-call model and effort overrides never change stored preferences. The helper supports an
alternate absolute `--gpt-exec` path, plus the wrapper's output options.

Review requests include the final diff and relevant new files, the starting
state, approved requirements, and system documents. Review objectives are:

- Functional correctness, regressions, edge cases, and supporting verification.
- Alignment with the product requirement document and system documents. Report unavailable
  documents as a coverage gap; use explicit requirements and the approved plan as available evidence.
- Security limited to API-secret confidentiality, including exposure through source control,
  client output, logs, errors, or unintended recipients. Redact secret values in findings.

Require actionable findings with location, evidence, impact, and suggested corrections, or an
explicit no-findings result. The executor resolves findings and obtains focused re-review, or
records the user's explicit acceptance. The reviewer makes no edits. Missing configuration or
failed invocation cannot be reported as a successful review.

## Installation and verification

Tool installation and role initialization are separate user actions. The installer defaults
to `~/.local/bin`, supports a temporary absolute destination for testing, and refuses to overwrite
existing executables unless `--force` is supplied. `--bin-dir` selects the test or alternate
destination. It never changes shell profiles, publishes model environment variables, or rewrites
role preferences.

Tests cover creation, partial updates, preserved values, invalid input, lock contention, atomic
updates, and failure cleanup. Wrapper tests use a stub executable and include an inherited stdin
pipe whose writer stays open: the prompt must still arrive and the process must exit promptly.
Also verify paths with spaces, missing executables, invalid prompt sources, exact arguments,
sandbox selection, nonzero exits, and cancellation. No paid model calls are needed for these checks.

The planning scripts expose graph construction, text parsing, and plan validation as Python
functions. Their existing CLI names remain available. `task_dag.py --input FILE` loads JSON from a
file, and only explicit `--input -` reads stdin. Graph validation rejects redundant transitive
edges and invalid categories regardless of the entry point. One shared fence-aware view prevents
Markdown examples from being interpreted as task headings, table rows, fields, or placeholders.

## References

| Reference | Use for |
| --- | --- |
| Local `/usr/bin/plutil -help` and `man plutil` | Typed JSON extraction and conversion. Use conversion to validate JSON; `-lint` rejects JSON on the tested version. |
| [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode) | Prompt input, progress, final output, and automation behavior. |
| [OpenAI model catalog](https://developers.openai.com/api/docs/models) | The requested model ID and reasoning support. |

Implementation sequence: [execution plan](subagent-model-selection-plan.md).
