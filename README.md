# agent-workbench

Personal tools that improve the AI-agent experience: reusable skills, instructions, and MCP
servers kept in one place instead of being re-derived or copied between projects.

## What lives here

| Directory | Contents |
| --- | --- |
| [`skills/`](skills/) | [Agent Skills](https://agentskills.io) folders — one directory per skill |
| [`instructions/`](instructions/) | Instruction documents read by an agent — working conventions, review and reporting formats, authoring rules |
| [`mcp/`](mcp/) | Local MCP servers that expose structured tools to compatible clients |

The documentation writer MCP is installed independently with `install-mcp.sh`; the general
`install.sh` continues to install only skills and instructions.

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

Where a destination already exists the script lists every collision and asks once, defaulting to
overwrite; answering `n` skips all existing items and installs the rest. Skill folders are replaced
whole, so a file deleted here does not survive in an install.

Restart the client afterwards — skills and rules are read at session start.

## Install the documentation writer MCP

`install-mcp.sh` independently installs the local `documentation-writer` stdio server and registers
it with Codex, Claude Code, and Cursor. It supports macOS only. Python 3.10+ and an authenticated Codex
CLI must already be available; user-scope Claude Code registration also requires the `claude` CLI.

```bash
./install-mcp.sh /path/to/project
./install-mcp.sh --scope project --client codex,claude /path/to/project
./install-mcp.sh --scope user
./install-mcp.sh --scope user --client cursor
```

Project scope installs the runtime at
`<project>/.agents/mcp/documentation-writer/` and writes the selected client registrations to
`<project>/.codex/config.toml`, `<project>/.mcp.json`, and `<project>/.cursor/mcp.json`. User scope
installs under `~/Library/Application Support/agent-workbench/mcp/documentation-writer/` and updates
the corresponding user configurations. `--client all` is the default.

The server exposes `write_project_documentation`. A caller supplies finalized changes, changed
component summaries, target documents, and an evidence manifest of absolute file paths. The server
validates those boundaries, launches Codex with `gpt-6-sol` and medium reasoning, and rejects a run
that changes anything outside the named target documents. See
[`mcp/documentation-writer/README.md`](mcp/documentation-writer/README.md) for the brief contract.

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

## Contributing back

Anything added here must be **general**: it must make sense in a repository that knows nothing
about the project it came from. A skill, instruction, or MCP server that names a specific spec file,
product, or directory layout belongs in that project, not in this one. Where a rule is genuinely
useful but carries a project-specific detail, state the rule by the role the artifact plays rather
than by its path — and never by the location it happens to be installed to, which varies with the
environment.
