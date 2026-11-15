---
name: project-metadata-guideline
description: Keep product requirements, system design, and project configuration in a fixed document tree, and change those documents only after the user approves a change preview. Always apply — whenever the user states a requirement or a design, deployment, build, test, packaging, or tooling decision; whenever work adds, changes, or retires a capability, concept, contract, data model, flow, quality target, or development decision; and whenever a spec, plan, figure, fixture, or HTML exhibit is written.
always: true
---

# Project metadata guideline

**Objective.** Keep the project's major concepts, design and deployment decisions, and development
decisions in a fixed set of documents, so later sessions find them in one place. Change those
documents only with the user's explicit consent to the exact text.

**Your tasks.** Place the project documents, decide what enters them, organize related content into
numbered document sections, preview each change and get consent, write approved sections, work
against the documents, and place plans and authored resources.

## 1. Place the project documents

Keep these files, relative to the project root. Creating a missing file is your job: create it when
its first numbered document section is approved.

| File | Holds |
| --- | --- |
| `project_metadata/product/functional.md` | What the product does and for whom. |
| `project_metadata/product/non_functional.md` | How well the product must behave. |
| `project_metadata/system_design/functional.md` | How the running system delivers the product's functions. |
| `project_metadata/system_design/non_functional.md` | How the running system meets each product quality. |
| `project_metadata/project_configuration.md` | How the project is built, tested, packaged, and developed. |

## 2. Decide what enters project documents

A **numbered document section** is a `## <number>. <title>` block inside one of the files in section
1. Treat a numbered document section, not an individual clause, as the unit of documentation.

Propose a project-document change only when it records a durable, high-level product goal,
system-design or deployment decision, or project-configuration decision that future work must
preserve. Use the same entry condition whether the user, you, or another skill proposed the
content. A proposal never authorizes writing it; section 4 owns consent.

Do not include code references, temporary task details, low-level implementation or configuration
facts, or any requirement or decision the user has not approved through the change preview.

### Organize the numbered document sections

Group related requirements and decisions around one durable goal. A numbered document section may
contain several classifications when they serve that goal. Use only the classifications that have
content, as `###` headings inside the numbered document section. Never split related content merely
because it has different classifications.

- In `product/functional.md`, organize numbered document sections by product goal or cohesive
  feature. Classify their content as Actors, Capabilities, Concepts, or Exclusions.
- In `product/non_functional.md`, organize numbered document sections by quality objective.
  Classify their content as Latency, Throughput, Reliability, Availability, Security and privacy,
  Compatibility, Accessibility, or Compliance. Give each quality a measurable threshold and the
  condition it holds under. Ask for either one when it is missing.
- In `system_design/functional.md`, organize numbered document sections by major design area that
  delivers a product goal. Classify their content as Structure, Interfaces, Data, or Flows.
- In `system_design/non_functional.md`, organize numbered document sections by operating strategy
  that serves a product quality objective. Classify their content as Capacity, Resilience,
  Security, Observability, or Deployment. Name the product numbered document section each strategy
  serves.
- In `project_configuration.md`, organize numbered document sections by cohesive development
  decision area. Classify their content as Build, Test, Packaging, Development, or Toolchain.

### Choose the section change

- **Add:** When the proposal introduces a distinct, durable goal or major decision that no existing
  numbered document section covers, then add a numbered document section.
- **Update:** When an existing numbered document section represents the same goal or decision area,
  then update it. Use an update when adding, changing, or retiring only part of its content.
- **Remove:** When the complete goal or decision represented by a numbered document section is
  retired, then remove it. Never renumber the remaining numbered document sections.
- **Merge:** When multiple numbered document sections represent the same goal or decision area,
  then merge them. Retain the lowest existing section number, update that section with the
  consolidated content, and remove the redundant sections. Represent the merge in the preview as
  one `update` and one `remove` for each redundant section.

## 3. Compose the numbered document sections

Give every numbered document section a stable integer and a title that names its goal or decision,
such as `## 2. Search and discovery`. For a new section, use the next unused integer. Never reuse a
retired number or renumber existing sections.

Open with a short statement of the goal or decision. Follow it with the applicable classification
headings and their related requirements or decisions. Keep the section cohesive; never give each
sentence its own identifier.

Cite another numbered document section as `<path under project_metadata/> §<number>, <title>`, such
as `product/non_functional.md §2, Search performance`. Keep each file a snapshot of current
requirements and decisions, never a version history.

## 4. Preview the change and get consent

Before adding, updating, or removing a numbered document section, show one summary row per operation:

| Document | Section | Change |
| --- | --- | --- |
| `product/functional.md` | `2. Search and discovery` | update |
| `system_design/functional.md` | `4. Search execution` | add |

`Change` is `add`, `update`, or `remove`. After the table, show the complete proposed section for
each `add` and `update`, and the complete current section for each `remove`. Present the preview
before code or data work that depends on it. When a decision emerges during work, present the
preview before the task ends.

Ask `Record these changes? [1. Yes / 2. No]` and wait.

- On `1`, write exactly the previewed changes.
- On `2`, write nothing. Ask which operations to revise or drop, then show the preview again.
- Never add, update, or remove a numbered document section without a `1` to the preview that showed
  that operation and its complete text.
- Never treat a stated requirement, an approved plan, or a finished task as consent.

## 5. Work against the documents

- Before modifying code or performing a CRUD data operation, read the matching project documents.
- When a document and the implementation disagree, state which one is defective and fix that one.
  Fix a document only through section 4. Never silently reword a numbered document section to match
  the implementation.
- When a proposed change conflicts with or duplicates an existing numbered document section, show
  both and ask the user to reconcile them.
- When a coding task completes or a code review begins, validate the changes against the product and
  system-design numbered document sections.
- Never test or run experiments for a non-functional requirement, such as latency or throughput,
  unless the user explicitly requests it.

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
