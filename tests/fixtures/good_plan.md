# Execution Plan — Ship the config parser

## Problem Statement

The loader reads settings by hand in three places, so a malformed file fails at a different point
each time and the error never names the field. A single parser gives one failure path and one
message.

**Goals**

| Goal | Tasks |
|---|---|
| setup | T1, T2 |
| ship | T3 |

## Task DAG

| Task # | Goal | Category | Task | Depends on | Success criterion |
|---|---|---|---|---|---|
| T1 | setup | code | parser | — | `python3 -m unittest tests.test_parser` passes with 4 cases |
| T2 | setup | config | ci | T1 | a pull request on this repo shows the `unit` job green |
| T3 | ship | docs | notes | T2 | `README.md` documents the parser entry point and its two flags |

## Task Execution

| Task # | Executor | Rationale |
|---|---|---|
| T1 | subagent | Parser and its tests are a self-contained coding workstream |
| T2 | main-agent | The CI change must be reconciled with shared project configuration |
| T3 | main-agent | The final wording depends on the completed implementation |

## Tasks

### T1 parser

**Files**

- src/parser.py
- tests/test_parser.py

**Consumes**

- —

**Produces**

- `parse_config(path)`, raising `ConfigError` with the offending field name

**Verify**

- `python3 -m unittest tests.test_parser`

### T2 ci

**Files**

- .github/workflows/ci.yml

**Consumes**

- `tests/test_parser.py` from T1

**Produces**

- A `unit` job that runs on every pull request

**Verify**

- Open a draft pull request and confirm the `unit` job runs and passes

### T3 notes

**Files**

- README.md

**Consumes**

- `parse_config(path)` and its flags from T1

**Produces**

- —

**Verify**

- `grep -n "parse_config" README.md`

## Spec Sync

| Clause | Document | Change | Driven by |
|---|---|---|---|
| Configuration file format and its error reporting | product requirements | amend | T3 |

## Execution Guidelines

Do not start any task until `Confirm plan? [1. Yes / 2. No]` has been answered `1`. Wait for the
answer. On `2`, revise the plan; start no task.

This plan has a spec sync task. Show the `## Spec Sync` table and ask
`Confirm spec update? [1. Yes / 2. No]` before any task starts. On `2`, drop that task, write one
line here saying why, and re-run the tool so the numbering stays generated.

Goals are serial. Within a goal, ready tasks with no edge and no overlapping files may run in
parallel. Launch ready `subagent` tasks together. Keep integration and final synthesis on the main
agent.

On a wrong or missing edge, fix the pairs, re-run the tool, and replace the tables. Never patch
numbering by hand.
