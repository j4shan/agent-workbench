# coding-harness

Reusable configuration for AI coding agents — the parts that are worth carrying from one project
to the next, kept in one place instead of being re-derived or copy-pasted per repository.

## What lives here

| Directory | Contents |
| --- | --- |
| [`skills/`](skills/) | [Agent Skills](https://agentskills.io) folders — one directory per skill |
| [`instructions/`](instructions/) | Instruction documents read by an agent — working conventions, review and reporting formats, authoring rules |
| [`subagents/`](subagents/) | Cursor subagent definitions — Markdown files a parent agent can delegate to |
| [`tests/`](tests/) | Tests over the executable helpers that skills ship — run from the repository root, never installed into a target project |

MCP server definitions are also in scope for this repository; no directory has been designated for
them yet.

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
the *consuming* project's root. Tests over those helpers live in [`tests/`](tests/) at this
repository's root instead, which `install.sh` does not copy, so they never reach a target project.
Run them with `python3 -m unittest discover tests`.

The `description` is what a client matches a task against, so it states both what the skill
produces and the situations that should trigger it — including phrasings a user would actually
type rather than the skill's own name. A skill with `always: true` must load in every session.
A skill with `disable-model-invocation: true` is the other exception: the agent must not apply
it from context. It loads only when the user types `/<name>` in chat.

Bundled skills:

| Skill | Purpose |
| --- | --- |
| `execution-planning` | Build execution plans and task DAGs for multi-step work. |
| `problem-presentation-format` | Report defects and open decisions in a fixed numbered layout. |
| `project-metadata-guideline` | Place project-owned docs and assets in a fixed tree (`always: true`). |
| `technical-writing` | Produce teaching-style technical explanations. |
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

### Subagents

One Markdown file per worker, with YAML frontmatter (`name`, `description`, and optional `model`)
followed by the prompt body. Cursor loads these when a parent agent delegates a task into an
isolated context.

```
subagents/
  <name>.md
```

Subagents are **opt-in at install time**. They copy only when `install.sh` is run with
`--subagent`. A `README.md` in this directory is never installed.

## Install

`install.sh` copies skills and instructions into either a **target project** (default) or the
**current user's** client directories. Pass `--subagent` to also copy Cursor subagent definitions.

```bash
./install.sh /path/to/project
./install.sh --scope project /path/to/project
./install.sh /path/to/project execution-planning
./install.sh /path/to/project execution-planning,another-skill
./install.sh --scope project --subagent /path/to/project
./install.sh --scope user
./install.sh --scope user execution-planning
./install.sh --scope user --subagent
```

`--scope project` (the default) requires a project directory. `--scope user` takes no project
directory; a leftover argument that is a directory is an error. Omit the skill list to install
every included skill. A comma-separated list installs only those named skills; an unknown name is
an error.

[`install.yaml`](install.yaml) is the inclusion list. Each skill, instruction, and subagent
defaults to `true`. Set a name to `false` to skip it. An item on disk but missing from the file
is still installed.

The script refuses a project-scope install into this repository itself.

**Project** (`--scope project`):

| | Destination |
| --- | --- |
| **Skills** | `<project>/.agents/skills/<name>/` |
| **Cursor rules** | `<project>/.cursor/rules/<name>.mdc` |
| **Claude Code rules** | `<project>/.claude/rules/<name>.md` |
| **Subagents** (`--subagent`) | `<project>/.cursor/agents/<name>.md` |

**User** (`--scope user`):

| | Destination |
| --- | --- |
| **Skills** | `~/.cursor/skills/<name>/` and `~/.claude/skills/<name>/` |
| **Cursor rules** | `~/.cursor/rules/<name>.mdc` |
| **Claude Code rules** | `~/.claude/rules/<name>.md` |
| **Subagents** (`--subagent`) | `~/.cursor/agents/<name>.md` |

Cursor and Codex load `.agents/skills/` natively at project scope. Claude Code's documented
project skill path is `.claude/skills/`; a project-scope install does not write a second skill
copy there, because Cursor also scans that directory and would register the same skill twice. A
user-scope install writes both home directories, because each client only scans its own.

Instructions are given to each client in the shape it loads: verbatim for Claude Code, and wrapped
in `description` / `alwaysApply` frontmatter for Cursor. A `README.md` in a source directory is
never installed.

Paths written inside a skill are relative to the *consuming* project's root —
`.agents/skills/<name>/scripts/…` — because that is where the shell starts.

Where a destination already exists the script lists every collision and asks once, defaulting to
overwrite; answering `n` skips all existing items and installs the rest. Skill folders are replaced
whole, so a file deleted here does not survive in an install.

Restart the client afterwards — skills, rules, and subagents are read at session start.

After a **project-scope** install, if earlier copies still exist at **user scope**, the script
prints `rm` commands for those paths and does not delete them. Run the printed commands if you no
longer want those skills, rules, and subagents applied to every project on the machine:

```bash
rm -rf ~/.cursor/skills/execution-planning
rm -rf ~/.claude/skills/execution-planning
rm -rf ~/.cursor/skills/problem-presentation-format
rm -rf ~/.claude/skills/problem-presentation-format
rm -rf ~/.cursor/skills/project-metadata-guideline
rm -rf ~/.claude/skills/project-metadata-guideline
rm -f  ~/.cursor/agents/cursor-grok-4.6-high.md
```

Earlier installs wrote those two as Cursor `.mdc` and Claude `.md` rule files. Those copies
are not updated by a skill install. Remove them if they are still present:

```bash
rm -f ~/.cursor/rules/problem-presentation-format.mdc \
      ~/.cursor/rules/project-metadata-guideline.mdc
rm -f ~/.claude/rules/problem-presentation-format.md \
      ~/.claude/rules/project-metadata-guideline.md
```

## Contributing back

Anything added here must be **general**: it must make sense in a repository that knows nothing
about the project it came from. A skill, instruction, or subagent that names a specific spec file,
product, or directory layout belongs in that project, not in this one. Where a rule is genuinely
useful but carries a project-specific detail, state the rule by the role the artifact plays rather
than by its path — and never by the location it happens to be installed to, which varies with the
environment.
