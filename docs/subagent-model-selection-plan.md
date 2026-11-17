# Execution Plan — User-scoped subagent models and reliable Codex invocation

## Problem Statement

The documentation writer pins a model in its invocation. Delegating skills lack a shared,
user-owned role configuration and a reliable invocation boundary for non-interactive stdin.
The execution-planning skill also needs the requested final implementation review. Implement
[the design proposal](subagent-model-selection-design.md) while keeping configuration, invocation,
and task instructions separate.

**Goals**

| Goal | Tasks |
|---|---|
| configure | T1 |
| invoke | T2 |
| distribute | T3, T4 |
| adopt | T5 |
| verify | T6 |

**Constraints**

- Use `skills/` and `tools/` directory prefixes without introducing a standalone delegation skill.
- Store structured user-level configuration and retrieve it with a native macOS command at a known path.
- Use GPT-6.1 Sol with high reasoning for the content-writer role; keep role choices centrally configurable.
- Limit review security objectives to API-secret confidentiality.
- Preserve the existing artifact names and the current AGENTS.md changes.

## Task DAG

| Task # | Goal | Category | Task | Depends on | Success criterion |
|---|---|---|---|---|---|
| T1 | configure | code | model-upsert | — | Creation, partial updates, concurrent writers, and failed updates preserve valid role files. |
| T2 | invoke | code | gpt-invocation | T1 | An invocation with inherited open stdin completes from its prompt file with exact settings and exit status. |
| T3 | distribute | code | tool-installation | T2 | An isolated installation produces executable commands without changing role preferences or shell profiles. |
| T4 | distribute | docs | usage-guide | T3 | Usage instructions cover setup, direct retrieval, invocation, and recovery with executable examples. |
| T5 | adopt | docs | skill-adoption | T4 | Both skills retrieve role settings and compose complete commands; the writer has no pinned model and plans include the specified final review. |
| T6 | verify | code | integration-review | T5 | Integration checks pass and scoped review findings are resolved or explicitly accepted, with coverage gaps reported. |

## Tasks

### T1 model-upsert

**Files**

- tools/subagent-model-upsert.sh
- tools/tests/test-subagent-model-upsert.sh

**Consumes**

The approved two-string JSON array and robust-upsert contracts in the design proposal. Implement
Bash 3.2-compatible parsing and native JSON-array operations through plutil. Use the documented default directory and
validate the optional absolute directory override. Require complete new records; patch only supplied
elements in existing valid pairs. Preserve the unspecified element and reject extra elements. Use a bounded per-role lock,
validate a same-directory temporary file, and atomically rename it. Cleanup only owned resources;
leave existing configuration intact on failure. Tests use temporary directories, never the real
user configuration.

**Produces**

A reusable upsert command and isolated tests; two-string JSON role files consumable directly by plutil.

**Verify**

Run `/bin/bash tools/tests/test-subagent-model-upsert.sh`. Cover creation, partial updates,
preserved values, malformed pairs, extra or missing elements, invalid names, file permissions,
lock timeout, concurrent updates, and interrupted or failed writes. Validate resulting JSON with
`/usr/bin/plutil -convert json -o /dev/null`.

### T2 gpt-invocation

**Files**

- tools/gpt-exec.sh
- tools/tests/test-gpt-exec.sh

**Consumes**

The invocation interface in the design proposal and the installed Codex CLI's current help.
Require an explicit model, effort, sandbox, project, and readable nonempty regular prompt file.
Build arguments with an array and replace the wrapper with Codex, supplying `-` and redirecting
stdin from the prompt file. Keep scheduling with the caller. Preserve authentication, other user
configuration, runtime status, and signals. Support the documented output options. Never retrieve
role settings or silently retry inside this wrapper.

**Produces**

A shared invocation command with a deterministic stdin contract and stub-runtime tests.

**Verify**

Run `/bin/bash tools/tests/test-gpt-exec.sh`. A stub Codex must receive the exact prompt and
arguments while the wrapper inherits a pipe whose writer remains open. Give this regression test a
short bounded deadline. Verify paths with spaces, FIFO rejection, empty or missing prompts, missing
Codex, settings validation, both supported sandboxes, output options, nonzero exits, and cancellation.
Make no model calls.

### T3 tool-installation

**Files**

- tools/install-tools.sh
- tools/tests/test-install-tools.sh

**Consumes**

The completed upsert and invocation scripts. Implement a separate explicit user-tool installer
with a default destination of the user's `.local/bin` directory and an absolute destination override
for tests. Install the two commands under their documented names and executable permissions. Refuse
overwriting existing commands unless explicitly requested. Preserve role configuration and shell
profiles. Keep the existing skill installer and inclusion file unchanged.

**Produces**

An explicit tool installation command with tests for fresh installs, conflicts, and upgrades.

**Verify**

Run `/bin/bash tools/tests/test-install-tools.sh` against temporary destinations. Verify the
installed commands work with temporary role configuration and a stub runtime. Verify conflict handling
and explicit replacement, and assert existing preferences and shell-profile fixtures remain unchanged.

### T4 usage-guide

**Files**

- README.md

**Consumes**

The design proposal and installed-tool interface from the preceding task. Update only relevant
overview, tool-layout, and usage sections. Explain separate tool installation and explicit role upsert,
typed configuration retrieval, single-snapshot reads, per-call user overrides, the optional directory
override, and missing-config or stale-lock recovery. Include the requested content-writer setup and
the independently configurable reviewer setup. Link the design instead of copying its full contents.

**Produces**

User-facing setup and usage instructions consistent with the tested command interfaces.

**Verify**

Check each documented option and path against the implemented tools. Exercise setup, retrieval,
and invocation examples using a temporary configuration directory, temporary install destination, and
stub runtime. Do not initialize the real machine configuration.

### T5 skill-adoption

**Files**

- skills/documentation-writer/SKILL.md
- skills/execution-planning/SKILL.md

**Consumes**

The approved design and tool interfaces. In documentation-writer, replace the pinned model and
effort with typed direct reads from a single content-writer JSON-array snapshot, applying explicit user
overrides per field. Preserve its existing documentation-only scope and diff review. Give the skill
a complete gpt-exec command with workspace-write permissions and a finite request file.

In execution-planning, append a final read-only review goal to implementation plans, with generated
DAG dependencies after all implementation and verification. Bundle reviewer retrieval and invocation
in Python functions and include the helper's short invocation in generated plans. Specify functional correctness, alignment with the
PRD and system documents, and security limited to API-secret confidentiality. Handle missing evidence,
redacted findings, resolution, focused re-review, and explicit acceptance. Planning alone never
launches the reviewer. Report missing tools or settings instead of selecting a fallback model.

**Produces**

Two self-contained adopter skills using user-configured roles and the shared invocation command.

**Verify**

Inspect the final skill text for pinned model versions and incomplete invocation steps. Run the
examples with temporary preferences and a stub runtime. Generate an implementation-plan scaffold
containing the final read-only review goal and validate it with the existing plan checker. Confirm
prose-only work does not gain an implementation review requirement.

### T6 integration-review

**Files**

- —

**Consumes**

All completed tools, tests, skill changes, usage instructions, this approved plan, and the design
proposal. Install into a temporary destination and simulate writer and reviewer delegations against a
stub runtime. Inspect the final diff and relevant new files against the recorded starting state.
Review functional correctness, agreement with the approved design and explicit user requirements,
and API-secret confidentiality only. This repository has no separate PRD or system-document set for
this feature; state that evidence gap rather than creating one. Keep review read-only and assign any
corrections back to the original file owner before focused re-review.

**Produces**

An integration and review report with resolved or explicitly accepted findings and remaining coverage gaps.

**Verify**

Run all three tools/tests shell suites and `git diff --check`. Confirm changing a role file affects
the next invocation, both settings come from one snapshot, and an inherited open pipe cannot stall
prompt delivery. Report findings with file and line, evidence, impact, and correction, or explicitly
state no findings. Confirm no real model calls, machine installation, preference initialization, or
shell-profile changes occurred during these checks.

## Execution Guidelines

This is a proposal. Plan approval alone does not authorize execution. Start implementation only
when the user also requests it. Execution of this plan covers repository changes and isolated tests;
installing into the actual user home or initializing real role preferences remains a separate action.

Goals are serial. Use the generated dependencies and keep file ownership with the named task.
Compare the final workspace with its starting state and preserve unrelated changes, including
AGENTS.md. Do not create or install a delegation skill.

T6 is the final read-only review. Resolve actionable findings within the approved scope through
the original owners, run affected checks, and obtain focused re-review. Explicit user acceptance
is required for findings left open. Report coverage gaps and runtime behavior not exercised by
stub tests. Stop for user direction if a correction requires a new design decision.

The selected execution-planning skill requires: “Ask `Confirm plan? [1. Yes / 2. No]` and wait.”
On rejection, revise the plan and start no task. Approval covers this plan only.
