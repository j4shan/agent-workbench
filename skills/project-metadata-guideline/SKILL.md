---
name: project-metadata-guideline
description: Keep product requirements, system design, and project configuration in a fixed document tree, and change those documents only after the user approves a change preview. Always apply — whenever the user states a requirement or a design, deployment, build, test, packaging, or tooling decision; whenever work adds, changes, or retires a capability, concept, contract, data model, flow, quality target, or development decision; and whenever a spec, plan, figure, fixture, or HTML exhibit is written.
always: true
---

# Project metadata guideline

**Objective.** Keep the project's major concepts, design and deployment decisions, and development
decisions in a fixed set of documents, so later sessions find them in one place. Change those
documents only with the user's explicit consent to the exact text.

**Your tasks.** Place the project documents, propose entries by the taxonomy, preview each change
and get consent, write clauses in the shared format, work against the documents, and place plans
and authored resources. Each section states when it applies.

## 1. Place the project documents

Keep these files, relative to the project root. Creating a missing file is your job: create it when
its first clause is approved.

| File | Holds |
| --- | --- |
| `project_metadata/product/functional.md` | What the product does and for whom. |
| `project_metadata/product/non_functional.md` | How well the product must behave. |
| `project_metadata/system_design/functional.md` | How the running system delivers the product's functions. |
| `project_metadata/system_design/non_functional.md` | How the running system meets each product quality. |
| `project_metadata/project_configuration.md` | How the project is built, tested, packaged, and developed. |

Use the headings in section 2 as each file's `##` headings, in the order listed. Omit a heading
until it has a clause.

## 2. Propose an entry by the taxonomy

Propose a change to a project document whenever work adds, alters, or retires anything a heading
below names. Apply this whoever originated the change: the user, you, or another skill. File each
clause under the heading that matches what it asserts, never under the layer of code that
implements it. Never propose an entry for detail a reader can recover from the source, a manifest,
or a lockfile.

**`product/functional.md`**

| Heading | A clause states |
| --- | --- |
| Actors | Who uses the product, and what each role may see or do. |
| Capabilities | A task an actor can complete, and the rule that decides the result. |
| Concepts | An idea the product must remember or show, what it means, and how it relates to other concepts. |
| Exclusions | Something the product must not do, or a scope the user ruled out. |

**`product/non_functional.md`** — give each clause a measurable threshold and the condition it holds
under. When either is missing, ask for it before proposing the clause.

| Heading | A clause states |
| --- | --- |
| Latency | A response time a caller can observe. |
| Throughput | A rate of work the product must sustain. |
| Reliability | How often a result must be correct, and how durable data must be. |
| Availability | When the product must be usable, and how much downtime is acceptable. |
| Security and privacy | What must be protected, from whom, and how long data is kept. |
| Compatibility | The platforms, environments, and integrations the product must support. |
| Accessibility | An accessibility requirement the product must meet. |
| Compliance | A regulation or policy the product must meet. |

**`system_design/functional.md`**

| Heading | A clause decides |
| --- | --- |
| Structure | The runtime parts, what each owns, and which parts it depends on. |
| Interfaces | A contract a caller can rely on: operations, payloads, events, and error shapes. |
| Data | How a product concept is represented, identified, stored, and kept consistent. |
| Flows | The path a capability takes across parts, the states along the way, and what happens on failure. |

**`system_design/non_functional.md`** — name in each clause the product clause it serves.

| Heading | A clause decides |
| --- | --- |
| Capacity | Caching, scaling, and concurrency limits that meet a latency or throughput target. |
| Resilience | Redundancy, timeouts, retries, and failure containment that meet a reliability or availability target. |
| Security | Trust boundaries, authentication, encryption, and secret handling. |
| Observability | The logs, metrics, and traces that make a product quality checkable. |
| Deployment | Where the system runs, how many instances, which environments, and runtime configuration. |

**`project_configuration.md`**

| Heading | A clause decides |
| --- | --- |
| Build | How source becomes build outputs. |
| Test | Test layers, runners, and the checks that must pass. |
| Packaging | How outputs are assembled, versioned, and distributed. |
| Development | Local setup, contributor workflow, and the checks a contributor runs. |
| Toolchain | The chosen languages, frameworks, and developer tools. |

## 3. Preview the change and get consent

Apply before you add, update, or remove any clause in a project document. Present the preview before
the code or data change that depends on it. When a decision emerges during work, present it before
the task ends.

Show one row per clause:

| Document | Heading | Clause | Change | Text |
| --- | --- | --- | --- | --- |
| `product/functional.md` | Capabilities | `2.3` | add | A reviewer can approve a plan. |
| `system_design/non_functional.md` | Capacity | `1.1` | update | Cache search results for 60 s. Serves `product/non_functional.md#1.2`. |
| `project_configuration.md` | Test | `3.1` | remove | — |

`Change` is `add`, `update`, or `remove`. `Text` is the full new clause for `add` and `update`, and
`—` for `remove`.

Ask `Record these changes? [1. Yes / 2. No]` and wait.

- On `1`, write exactly the rows shown.
- On `2`, write nothing. Ask which rows to revise or drop, then show the preview again.
- Never add, update, or remove a clause without a `1` to a preview that showed that row.
- Never treat a stated requirement, an approved plan, or a finished task as consent.

## 4. Write clauses in the shared format

Apply whenever you write an approved clause.

- Give each clause a hierarchical dotted ID, such as `1.2.3`, unique within its file. IDs need not be
  contiguous.
- Record one decision per clause.
- Cite a clause in another file as `<path under project_metadata/>#<id>`, such as
  `product/non_functional.md#1.2`.
- Remove a retired or superseded clause. Never strike it through or annotate it, and never renumber
  the remaining clauses to fill the gap.
- Keep each file a snapshot of current decisions, never a version history.

## 5. Work against the documents

- Before modifying code or performing a CRUD data operation, read the matching project documents.
- When a document and the implementation disagree, state which one is defective and fix that one.
  Fix a document only through section 3. Never silently reword a clause to match the implementation.
- When a proposed change conflicts with or duplicates an existing clause, show both and ask the user
  to reconcile them.
- When a coding task completes or a code review begins, validate the changes against the product and
  system-design clauses.
- Never test or run experiments for a non-functional clause, such as latency or throughput, unless
  the user explicitly requests it.

## 6. Place plans and authored resources

- Put transient execution plans in `project_metadata/plans/`, relative to the project root. Create
  the directory when it does not exist. Never version these plans.
- Put project-owned writing and generation contracts in `project_metadata/instructions/`. Create the
  directory when it does not exist.
- Keep authored exhibit and fixture assets under `resources/`, relative to the project root. Never
  put temporary or git-ignored resources there.
  - Put authored HTML, canvases, and formal documents in `resources/html/`.
  - Put figures in `resources/img/`.
  - Put figure prompts in `resources/img_prompt/`.
  - Put authored scenario and fixture data in `resources/data/`. Never put runtime-generated data
    there.
