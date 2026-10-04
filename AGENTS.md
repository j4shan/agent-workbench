# Working in this repository

This repository holds agent configuration that ships to other projects. It carries two kinds of
artifact: **instruction documents** in [`instructions/`](instructions/), which load at the start of
every session, and **skills** in [`skills/`](skills/), which load when a task matches or, with
`always: true`, at the start of every session. See [README.md](README.md) for the layout and install
mechanics.

Write every shipped file for a project that knows nothing about where the file came from. A rule
that only makes sense in the project it was extracted from stays in that project.

## 0. Never create `project_metadata/` here

This rule outranks every other rule, in this file or in any always-on skill or instruction
document, and applies before you do anything else.

- Never create a `project_metadata/` directory in this repository, and never write a term dictionary
  or any other project-metadata file into one.
- Where an instruction document or a skill commands you to create or maintain such a file at a
  project-root path, that command does not fire here. Obey the rest of that document.
- This repository ships configuration to other projects; it is not a project those rules describe.
  Carry the vocabulary in the shipped files themselves — define a term where it is first commanded.
- When a term needs a definition a reader cannot infer, state it inline in the file that commands
  it, not in a separate index.

## 1. Pick the artifact kind

Apply when adding new guidance.

- Write a **skill** when the guidance holds while performing one named task, or when it must
  apply in every session. Set `always: true` in that latter case.
- Write an **instruction document** when a client must receive the guidance as a rule file
  rather than a skill. It spends permanent context, so it must earn permanent context.
- Write it into `README.md` when only a person needs it.
- Split guidance that mixes kinds: keep the always-true rule in a skill with `always: true` or
  in an instruction document, and move the on-demand procedure and its executable helpers into a
  skill.

## 2. Write commands, not narration

Apply to every instruction document and every skill body.

- Open with **Objective** — what the artifact achieves and why. Follow with **Your tasks** — the
  actions to perform.
- Give each action its own numbered section, titled with its imperative verb.
- Command the agent; do not describe the world. Write "Create a dictionary at `<path>`", not "At
  `<path>` is a dictionary".
- Attach the apply condition to the command: "Index a term only when all three conditions hold".
  Never leave the agent to infer when a rule fires.
- State a prohibition as a prohibition: "Never index a generated code symbol."
- Use simple words and short sentences. Cut hedges, restatement, and background the agent does not
  act on.

## 3. Name targets by role, not by location

Apply to every file that ships.

- Name a file the agent owns by a path relative to the project root.
- Say plainly that creating a missing file is the agent's job, not a precondition to wait on.
- Never name this repository, an install path such as `~/.claude/rules/`, or another project's
  configuration file. Where a file loads from varies with the environment; what it commands does not.
- Refer to a project artifact by the role it plays — "the product requirement document" — not by the
  filename one project happens to use.

## 4. Write the skill description for matching

Apply to every `skills/<name>/SKILL.md`.

- Give the frontmatter `name` and `description`. Add `always: true` when the skill must load in
  every session. Add `disable-model-invocation: true` when the skill must load only on explicit
  `/name` invocation. Add nothing else. Never set both.
- State in `description` both what the skill produces and the situations that should trigger it.
- Include the phrasings a user would actually type. Never make matching depend on the skill's own name.
- Keep executable helpers in the skill's own `scripts/`, and cite them by a path relative to the
  *consuming* project's root — `.agents/skills/<name>/scripts/<file>` — because that is where the
  shell starts.

## 5. Keep one subject per file

Apply to `instructions/`.

- Write one file per subject and name the file for the subject.
- State each rule in exactly one document. When a second document needs it, name the concept and let
  the owning document carry the rule.

## 6. Update the surrounding pieces in the same change

Apply when you add, rename, or delete a skill or an instruction document.

- Update the README section that describes it.
- Confirm `install.sh` still picks up skills and instructions: it discovers every
  `instructions/*.md` except `README.md` and every `skills/*/` holding a `SKILL.md`, then includes
  each name according to `install.yaml`. A name missing from the file is included. Change the
  script only when that shape changes, never to name a new file. Set the new name in `install.yaml`
  when it must not install by default.
- Define any new term inline, in the file that commands it. This repository keeps no term
  dictionary — see rule 0.
