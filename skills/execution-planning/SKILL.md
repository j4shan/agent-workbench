---
name: execution-planning
description: Use whenever a plan is being produced. Plan mode is active, or the user asks to plan a project, create an execution plan, break an objective into tasks, or build a task DAG. Produces serial functional goals, a dependency DAG, non-overlapping file ownership, observable success criteria, and a prose body saying how each task is done. Reach for this whenever multi-step work needs scoping, sequencing, or breaking down, even if the user never says "execution plan" or "DAG".
---

# Execution planning

**Objective.** Turn an objective into a written execution plan with serial functional goals, a task
DAG, non-overlapping file ownership, and observable success criteria. The plan is static. It carries
no status or run state.

**Your tasks.** Decompose the objective, build the DAG with the tool, then emit the plan and get it
approved.

## How this fits other planning guidance

The default planning procedure owns investigation. Read the code, find the real constraints, decide
how the work should be done, and write that how into each task body. The executor follows the body
and does not invent a second approach.

This skill owns decomposition, the dependency DAG, file ownership, and the document shape. Where
other guidance contradicts those points with an unordered task list, hand-drawn
ordering, or extra waves beyond serial goals, this skill wins.

## 1. Decompose

Name the functional goals in delivery order. Those rows are the plan's Goals table. Goals are
serial: goal 2 does not start until every task of goal 1 has finished. That serial goal is the only
wave. Do not invent others.

Give each goal at least one task. A task is the executable unit: a stable kebab-case id, a one-line
success criterion an observer could check rather than "implement X", and a prose body. Name the
work directly when it fits: `code-search`, `web-search`, `log-investigation`, `history-search`,
`production-source`, `test-code`, `integration`, `config`, `docs`, `assets`, or `external-wait`.

Every project file belongs to exactly one category:

- `code`, application source and the tests that prove that task
- `config`, build, CI/CD, dependency manifests, tooling config
- `docs`, human docs, agent instruction documents, and skills
- `assets`, static resources that are none of the above

Tie-break: `package.json` and CI go to `config`. Test files and fixtures go to `code`. README goes
to `docs`. Agent instruction documents and skills go to `docs`; their helper scripts and the tests
over them go to `code`.

Split rules:

- A writing task edits files in exactly one category. Every path in its body belongs to that
  category. A read-only search or wait task writes no files.
- Use at most one task per category in a goal, except `code`, which may have one
  `production-source` task and one `test-code` task. Their file lists must not overlap.
- Never give a task the product requirements, system design, or project configuration documents to
  edit. Changes to those documents follow their own preview and consent, outside the plan.
- Split production source from tests only when an agreed behavior or interface lets both proceed
  independently. Otherwise keep them in one `code` task.
- Prefer tasks verifiable without running anything downstream. Add a later `integration` task when
  combined verification is necessary; it owns no feature implementation.
- A wait on a person or an external system is a task with a success criterion, not a note outside
  the DAG.

## 2. Build the DAG

Capture only immediate intra-goal dependencies as pairs. `A > B` means A must finish before B
starts. Do not write transitive edges: if `A > B` and `B > C`, never add `A > C`. Do not write
cross-goal pairs. Do not work out the numbering yourself.

Run the tool. Its output is authoritative for numbering, ordering, and goal-cut edges. It lives in
this skill's directory, so pass the full path, since the shell starts in the project root:

```bash
python3 .agents/skills/execution-planning/scripts/task_dag.py \
  --goal-order add-cache,ship \
  --task add-cache:code:implement \
  --task add-cache:config:wire-ci \
  --task ship:docs:usage-notes \
  "implement > wire-ci"
```

While iterating on the graph, `--format pairs` prints the edges alone.

On `error: cycle detected: ...` the decomposition is circular. Fix the pairs and re-run. On an
empty goal, too many tasks in one goal and category, or a cross-goal pair, fix the input and re-run.
Never hand-edit the tool's output.

## 3. Emit the plan

Generate the document shell from the same tool, which fills in every derived cell so nothing is
transcribed by hand. Use the section 2 command with `--format scaffold --title "<objective>"` added.

Fill every placeholder in the tables and in each task body, then run the checker and fix everything
it reports:

```bash
python3 .agents/skills/execution-planning/scripts/check_plan.py <plan file>
```

The checker reads the document only. Judge the one thing it cannot: whether each success criterion
is observable.

Write the result to the plan file the host already has open. Plan mode provisions one and names it,
and that is the file the user will be shown. When the caller named a destination, write there.
Otherwise write `project_metadata/plans/<slug>.md`, relative to the project root, where `<slug>` is
a kebab-case name of the objective. Create `project_metadata/plans/` when it does not exist.

## 4. Get the plan approved

Ask `Confirm plan? [1. Yes / 2. No]` and wait. On `2`, revise the plan and start no task. On `1`,
stop unless the user also asked to execute. This approval covers the plan only.

## Plan document contract

These headings are the shared vocabulary between the agent that writes the plan and the agent that
later executes it, so keep them verbatim.

- `## Problem Statement` opens the plan: what is broken or missing today and why it is worth
  changing. Follow it with the Goals table, which is mandatory, then a Non-goals list only when the
  user supplied non-goals, then a Constraints list only when the project documents or the user
  named them. Never invent either list. Omit the block instead.
- Goals is `| Goal | Tasks |` in delivery order. `Tasks` lists the `Task #` values whose DAG `Goal`
  cell matches, and a blank cell is invalid. Goal ids here and in the DAG `Goal` column are the same
  strings in the same order.
- `## Task DAG` is the tool-generated table, unedited except for filling in each success criterion:
  `| Task # | Goal | Category | Task | Depends on | Success criterion |`. Never draw a separate
  dependency diagram.
- `## Tasks` comes after Task DAG and before Execution Guidelines, with one `### {Task #} {id}`
  subsection per task in `T` order. Each body has exactly Files, the create and modify paths in this
  task's category or `—` for read-only work; Consumes, prior artifacts or search scope; Produces,
  what later tasks rely on, or `—`; and Verify, the command or check that proves the success
  criterion. Do not add TDD step lists or pasted implementation code unless the user asked.
- `## Execution Guidelines` closes the plan. Goals are serial. Within a goal, ready tasks with no
  edge and no overlapping files may run in parallel.
