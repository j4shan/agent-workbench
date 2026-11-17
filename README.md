# agent-workbench

Personal tools that improve the AI-agent experience: reusable skills and instructions kept in one
place instead of being re-derived or copied between projects.

## What lives here

| Directory | Contents |
| --- | --- |
| [`skills/`](skills/) | [Agent Skills](https://agentskills.io) folders — one directory per skill |
| [`tools/`](tools/) | Shared shell commands and their tests |
| [`docs/`](docs/) | Designs and implementation plans |
| [`instructions/`](instructions/) | Instruction documents read by an agent — working conventions, review and reporting formats, authoring rules |

[`AGENTS.md`](AGENTS.md) carries the rules for authoring what lives here, addressed to an agent
working in this repository. `CLAUDE.md` is a symlink to it, so Claude Code and Cursor read one file.

### Skills

One directory per skill: a `SKILL.md` carrying YAML frontmatter (`name`, `description`) and the
skill body, plus its own `scripts/` where the skill ships executable helpers.

```
skills/
  <skill-name>/
    SKILL.md
    scripts/
```

A skill's `scripts/` are copied with it, so a skill cites its own helpers by a path relative to
the *consuming* project's root.

The `description` is what a client matches a task against, so it states both what the skill
produces and the situations that should trigger it — including phrasings a user would actually
type rather than the skill's own name. A skill with `always: true` must load in every session.
A skill with `disable-model-invocation: true` is the other exception: the agent must not apply
it from context. It loads only when the user types `/<name>` in chat.

Bundled skills:

| Skill | Purpose |
| --- | --- |
| `documentation-writer` | Delegate human-facing documentation using the user-configured `content-writer` role. |
| `execution-planning` | Build execution plans and task DAGs, including a final review for implementation changes. |
| `problem-presentation-format` | **Deprecated:** retained for reference and excluded from default installation. |
| `project-metadata-guideline` | Keep product, system-design, and project-configuration documents in a fixed tree, changed only after a confirmed preview (`always: true`). |
| `technical-writing` | **Deprecated:** retained for reference and excluded from default installation. |
| `visualize_with_drawio` | Create draw.io visualizations from written specifications. |

### Instructions

One file per subject, named for the subject. These are **always-on** rule files: once installed
they load at the start of every session in the project they were copied into, so each one must
earn permanent context. Prefer a skill with `always: true` when the same guidance can ship as a
skill. Guidance that only matters while performing a particular task belongs in a skill, which
loads on demand, or in this README, which is read by people. No instruction documents ship
today.

Write each one as a **paper of commands**, not a description of how things are:

- open with an **Objective** stating what the instruction achieves and why, then a **Your tasks**
  line naming the actions to perform;
- give each action its own numbered section, titled with the imperative verb;
- write every rule as a command with its condition attached — "Index a term only when all three
  hold", not "a term is admitted when";
- name any file the agent owns by a path **relative to the project root**, and say plainly that
  creating it is the agent's job rather than a precondition to wait on;
- never reference this repository, an installed location, or another project's configuration file.
  Where the instruction is read from varies with the environment; what it commands does not.

## Install

`install.sh` copies skills and instructions into either a **target project** (default) or the
**current user's** client directories.

```bash
./install.sh /path/to/project
./install.sh --scope project /path/to/project
./install.sh /path/to/project execution-planning
./install.sh /path/to/project execution-planning,another-skill
./install.sh --scope user
./install.sh --scope user execution-planning
```

`--scope project` (the default) requires a project directory. `--scope user` takes no project
directory; a leftover argument that is a directory is an error. Omit the skill list to install
every included skill. A comma-separated list installs only those named skills; an unknown name is
an error.

[`install.yaml`](install.yaml) is the inclusion list. Each skill and instruction
defaults to `true`. Set a name to `false` to skip it. An item on disk but missing from the file
is still installed.

The script refuses a project-scope install into this repository itself.

**Project** (`--scope project`):

| | Destination |
| --- | --- |
| **Skills** | `<project>/.agents/skills/<name>/` |
| **Cursor rules** | `<project>/.cursor/rules/<name>.mdc` |
| **Claude Code rules** | `<project>/.claude/rules/<name>.md` |

**User** (`--scope user`):

| | Destination |
| --- | --- |
| **Skills** | `~/.cursor/skills/<name>/` and `~/.claude/skills/<name>/` |
| **Cursor rules** | `~/.cursor/rules/<name>.mdc` |
| **Claude Code rules** | `~/.claude/rules/<name>.md` |

Cursor and Codex load `.agents/skills/` natively at project scope. Claude Code's documented
project skill path is `.claude/skills/`; a project-scope install does not write a second skill
copy there, because Cursor also scans that directory and would register the same skill twice. A
user-scope install writes both home directories, because each client only scans its own.

Instructions are given to each client in the shape it loads: verbatim for Claude Code, and wrapped
in `description` / `alwaysApply` frontmatter for Cursor. A `README.md` in a source directory is
never installed.

Paths written inside a skill are relative to the *consuming* project's root —
`.agents/skills/<name>/scripts/…` — because that is where the shell starts.

Use `documentation-writer` when asking an agent to delegate documentation writing or revision to
Codex. The skill supplies writing instructions, retrieves the user-configured `content-writer`
model and effort, and composes the complete `gpt-exec` invocation. Provide
the goal, target documents, and useful context in plain language, or use the optional annotated
JSON Schema in `skills/documentation-writer/references/brief.schema.json` for consistent requests.
The calling agent reviews the resulting prose and diff. A code change alone does not trigger
documentation delegation. Install the shared tools separately as described below.

Where a destination already exists the script lists every collision and asks once, defaulting to
overwrite; answering `n` skips all existing items and installs the rest. Skill folders are replaced
whole, so a file deleted here does not survive in an install.

Restart the client afterwards — skills and rules are read at session start.

After a **project-scope** install, if earlier copies still exist at **user scope**, the script
prints `rm` commands for those paths and does not delete them. Run the printed commands if you no
longer want those skills and rules applied to every project on the machine:

```bash
rm -rf ~/.cursor/skills/execution-planning
rm -rf ~/.claude/skills/execution-planning
rm -rf ~/.cursor/skills/problem-presentation-format
rm -rf ~/.claude/skills/problem-presentation-format
rm -rf ~/.cursor/skills/project-metadata-guideline
rm -rf ~/.claude/skills/project-metadata-guideline
```

Earlier installs wrote those two as Cursor `.mdc` and Claude `.md` rule files. Those copies
are not updated by a skill install. Remove them if they are still present:

```bash
rm -f ~/.cursor/rules/problem-presentation-format.mdc \
      ~/.cursor/rules/project-metadata-guideline.mdc
rm -f ~/.claude/rules/problem-presentation-format.md \
      ~/.claude/rules/project-metadata-guideline.md
```

## Shared tools and subagent models

The macOS tools require Bash 3.2 or later and native `plutil`; `gpt-exec` also needs Codex CLI on
`PATH`. Model choices are user-owned files, read directly at each invocation. They are not published
as environment variables. See the [design](docs/subagent-model-selection-design.md) for the contracts.

Install the commands, then explicitly create each role's configuration:

```bash
/bin/bash tools/install-tools.sh
"$HOME/.local/bin/subagent-model-upsert" \
  --role content-writer --model gpt-6.1-sol --reasoning-effort high
"$HOME/.local/bin/subagent-model-upsert" \
  --role code-reviewer --model gpt-6.1-sol --reasoning-effort high
```

Installation copies `subagent-model-upsert` and `gpt-exec` into `~/.local/bin`. It does not initialize
role files or change shell profiles. Existing commands require an explicit `--force` replacement.
Use `--bin-dir /absolute/directory` for another destination. The existing skill installer is unchanged.

Each role is stored at `~/Library/Application Support/subagent-models/<role>.json` as a fixed pair:

```json
["gpt-6.1-sol","high"]
```

Index `0` is the model; index `1` is the reasoning effort. The example selects GPT-6.1 High for
writing and proposes the same initial choice for review; the roles can be changed independently.
To change only one setting and preserve the other:

```bash
"$HOME/.local/bin/subagent-model-upsert" --role content-writer --reasoning-effort medium
```

Both settings are required when creating a role. Upsert validates the pair, serializes concurrent
writers, and atomically replaces the file. It rejects malformed existing settings. Role files use
mode `600` in a directory with mode `700`. `SUBAGENT_MODELS_DIR` optionally selects a different
nonempty absolute configuration directory; set it in the invoking process for both writes and reads.

The documentation writer uses `plutil` on the known file path. Reading one snapshot keeps model
and effort consistent if another process updates the role concurrently. For a role created by the
upsert tool:

```bash
role_dir="${SUBAGENT_MODELS_DIR-$HOME/Library/Application Support/subagent-models}"
case "$role_dir" in /*) ;; *) printf 'Configuration directory must be absolute\n' >&2; exit 1 ;; esac
role_config="$(/usr/bin/plutil -convert json -o - "$role_dir/content-writer.json")" || exit 1
model="$(/usr/bin/plutil -extract 0 raw -expect string -o - - <<< "$role_config")" || exit 1
effort="$(/usr/bin/plutil -extract 1 raw -expect string -o - - <<< "$role_config")" || exit 1
"$HOME/.local/bin/gpt-exec" \
  --model "$model" --reasoning-effort "$effort" \
  --sandbox workspace-write --project "$PWD" --prompt-file "$request_file"
```

The planning skill bundles `scripts/review.py`, which reads and validates the same JSON pair using
Python's standard library and invokes `gpt-exec` with read-only permissions. Its optional `--model`
and `--reasoning-effort` flags apply explicit user overrides; `--gpt-exec` supports an alternate
absolute tool path. It preserves process identity, runtime status, and cancellation.

Both skills include full pair-shape checks. An explicit per-call user override replaces only
the corresponding local variable before invocation; it does not update stored preferences. Missing
configuration or tools stop delegation with a setup error, without selecting another model.

`gpt-exec` requires a finite, nonempty regular prompt file and explicit model, effort, sandbox, and
project. It redirects stdin from that file, preventing a caller's open input pipe from stalling
prompt delivery. It preserves runtime exit status and cancellation; the calling process runner
manages scheduling and deadlines. Optional `--json` and `--output-last-message FILE` control output.
The wrapper logs selection metadata, not the prompt. Authentication stays with Codex. Inspect partial
edits after a failed invocation before retrying; the wrapper does not retry automatically.

`execution-planning` adds a final read-only implementation review covering functional correctness,
alignment with the PRD and system documents, and security limited to API-secret confidentiality.
Planning alone does not invoke it. Findings require correction or explicit user acceptance, and
missing evidence is reported as a coverage gap.

If upsert reports a lock timeout, verify that no writer is active before removing the indicated
empty lock directory with `rmdir`. Never clear another process's lock. Use `--lock-timeout SECONDS`
to adjust the wait from its 10-second default within the range 0–60. If a role file is malformed,
correct the reported two-string shape; upsert preserves the original on failure.

Run isolated tests with Python 3 available (the installed tools themselves do not require Python):

```bash
/bin/bash tools/tests/test-subagent-model-upsert.sh
/bin/bash tools/tests/test-gpt-exec.sh
/bin/bash tools/tests/test-install-tools.sh
python3 -m unittest discover -s skills/execution-planning/scripts/tests
```

These tests use temporary directories and a stub runtime, without model calls or changes to actual
user preferences.

The planning helpers also expose reusable Python functions: `task_dag.build()` constructs and
validates a graph, `plan_doc.parse()` parses plan text, and `check_plan.validate_plan()` returns
findings without printing. The graph CLI accepts `--input FILE` or explicit `--input -` for JSON
stdin; its existing task and output options remain available. It never reads stdin implicitly.

## Contributing back

Anything added here must be **general**: it must make sense in a repository that knows nothing
about the project it came from. A skill or instruction that names a specific spec file, product, or
directory layout belongs in that project, not in this one. Where a rule is genuinely
useful but carries a project-specific detail, state the rule by the role the artifact plays rather
than by its path — and never by the location it happens to be installed to, which varies with the
environment.
