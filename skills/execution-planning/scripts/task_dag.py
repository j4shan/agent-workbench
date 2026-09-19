#!/usr/bin/env python3
"""Build a numbered task table from goals, category tasks, and intra-goal edges.

Pass tasks as `goal:category:id` and pairs as `prerequisite > dependent`.
The tool numbers every task `T1`, `T2`, … so a prerequisite always sits above
the work that waits on it, then prints one markdown row per task.

Goals are serial. Category tasks are the only parallel dimension. This tool
inserts a goal-cut edge from every sink of goal *i* to every source of goal
*i+1*. Write only intra-goal pairs; do not add those cuts by hand.

Each row shows the work that must finish before that task can start, including
goal-cut edges. The table states what is true when the plan is written, so it
carries no status column and no reverse-edge column.

Categories are `code`, `config`, `docs`, `assets`. A goal may have at most one
task per category, except `code`, which may have two.

Usage:
    task_dag.py --goal-order add-cache,ship \\
        --task add-cache:code:implement --task add-cache:config:wire-ci \\
        --task ship:docs:spec-sync "implement > wire-ci"
    task_dag.py --format scaffold --title "Add caching" \\
        --task add-cache:code:implement --task add-cache:docs:notes
    echo '{"goals":["g"],"tasks":[{"id":"a","goal":"g","category":"code"}],"edges":[]}' \\
        | task_dag.py
    task_dag.py --format table --task g:code:a --task g:config:b "a > b"

A cycle, an empty goal, too many tasks in one goal and category, or a cross-goal
pair exits with status 1.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

SEPARATORS = ("->", ">")
CATEGORIES = ("code", "config", "docs", "assets")


class Slice:
    __slots__ = ("id", "goal", "category")

    def __init__(self, id: str, goal: str, category: str) -> None:
        self.id = id
        self.goal = goal
        self.category = category


def parse_pair(raw: str) -> tuple[str, str]:
    for sep in SEPARATORS:
        if sep in raw:
            head, _, tail = raw.partition(sep)
            head, tail = head.strip(), tail.strip()
            if not head or not tail:
                raise ValueError(f"incomplete dependency pair: {raw!r}")
            return head, tail
    raise ValueError(f"not a dependency pair (expected 'A > B'): {raw!r}")


def parse_slice(raw: str) -> Slice:
    parts = raw.split(":", 2)
    if len(parts) != 3 or not all(p.strip() for p in parts):
        raise ValueError(f"not a slice (expected 'goal:category:id'): {raw!r}")
    goal, category, name = (p.strip() for p in parts)
    if category not in CATEGORIES:
        raise ValueError(f"unknown category {category!r} (expected {', '.join(CATEGORIES)})")
    return Slice(name, goal, category)


def parse_goal_order(raws: Sequence[str]) -> list[str]:
    order: list[str] = []
    for raw in raws:
        for part in raw.split(","):
            name = part.strip()
            if name and name not in order:
                order.append(name)
    return order


def _slices_from_json_tasks(tasks: object) -> list[Slice]:
    if not isinstance(tasks, list):
        raise ValueError("JSON 'tasks' must be a list of {id, goal, category} objects")
    slices: list[Slice] = []
    for item in tasks:
        if not isinstance(item, dict):
            raise ValueError("JSON tasks must be objects {id, goal, category}")
        name, goal, category = item.get("id"), item.get("goal"), item.get("category")
        if not name or not goal or not category:
            raise ValueError(f"JSON task missing id, goal, or category: {item!r}")
        if category not in CATEGORIES:
            raise ValueError(f"unknown category {category!r} (expected {', '.join(CATEGORIES)})")
        slices.append(Slice(str(name), str(goal), str(category)))
    return slices


def insert_goal_cuts(
    slices_by_id: dict[str, Slice],
    prereqs: dict[str, list[str]],
    dependents: dict[str, list[str]],
    goal_order: list[str],
) -> list[tuple[str, str]]:
    """Link every sink of goal i to every source of goal i+1."""
    by_goal: dict[str, list[str]] = {goal: [] for goal in goal_order}
    for name, sl in slices_by_id.items():
        by_goal[sl.goal].append(name)

    cuts: list[tuple[str, str]] = []
    for i in range(len(goal_order) - 1):
        ids_a = by_goal[goal_order[i]]
        ids_b = by_goal[goal_order[i + 1]]
        set_a, set_b = set(ids_a), set(ids_b)
        sinks = [n for n in ids_a if not any(d in set_a for d in dependents[n])]
        sources = [n for n in ids_b if not any(p in set_b for p in prereqs[n])]
        for src in sinks:
            for dst in sources:
                if dst in dependents[src]:
                    continue
                dependents[src].append(dst)
                prereqs[dst].append(src)
                cuts.append((src, dst))
    return cuts


def build(
    edges: list[tuple[str, str]],
    slices: list[Slice],
    goal_order: list[str],
) -> dict:
    """Number slices so every prerequisite comes before its dependents.

    When two slices are both ready, the one named first in the input wins.
    Ready slices are taken as a group, not one at a time. Independent slices
    then sit next to each other in the numbering. Goal-cut edges make later
    goals wait on earlier ones; that is the schedule.
    """
    if not slices:
        raise ValueError("no tasks given")

    seen_ids: list[str] = []
    slices_by_id: dict[str, Slice] = {}
    for sl in slices:
        if sl.id in slices_by_id:
            raise ValueError(f"duplicate task id: {sl.id!r}")
        seen_ids.append(sl.id)
        slices_by_id[sl.id] = sl

    if not goal_order:
        inferred: list[str] = []
        for sl in slices:
            if sl.goal not in inferred:
                inferred.append(sl.goal)
        goal_order = inferred
    else:
        goal_order = list(dict.fromkeys(goal_order))

    unknown_goals = sorted({sl.goal for sl in slices} - set(goal_order))
    if unknown_goals:
        raise ValueError(f"task goal not in --goal-order: {', '.join(unknown_goals)}")

    for goal in goal_order:
        if not any(sl.goal == goal for sl in slices):
            raise ValueError(f"empty goal: {goal!r}")

    pair_seen: dict[tuple[str, str], list[str]] = {}
    for sl in slices:
        key = (sl.goal, sl.category)
        pair_seen.setdefault(key, []).append(sl.id)
        limit = 2 if sl.category == "code" else 1
        if len(pair_seen[key]) > limit:
            raise ValueError(
                f"too many tasks in goal {sl.goal!r} for category {sl.category}: "
                f"{', '.join(pair_seen[key])}"
            )

    for src, dst in edges:
        if src not in slices_by_id or dst not in slices_by_id:
            missing = src if src not in slices_by_id else dst
            raise ValueError(f"edge names a task that is not a slice: {missing!r}")
        if slices_by_id[src].goal != slices_by_id[dst].goal:
            raise ValueError(
                f"cross-goal pair {src!r} > {dst!r}: write only intra-goal edges; "
                "goal order is serial and the tool inserts the cut"
            )

    # Declaration order: goal order, then first mention inside each goal.
    order_seen: list[str] = []
    for goal in goal_order:
        for name in seen_ids:
            if slices_by_id[name].goal == goal and name not in order_seen:
                order_seen.append(name)

    prereqs: dict[str, list[str]] = {name: [] for name in order_seen}
    dependents: dict[str, list[str]] = {name: [] for name in order_seen}
    planner_edges = list(dict.fromkeys(edges))
    for src, dst in planner_edges:
        if src not in prereqs[dst]:
            prereqs[dst].append(src)
            dependents[src].append(dst)

    cut_edges = insert_goal_cuts(slices_by_id, prereqs, dependents, goal_order)
    all_edges = list(dict.fromkeys([*planner_edges, *cut_edges]))

    ordered: list[str] = []
    placed: set[str] = set()
    remaining = list(order_seen)
    while remaining:
        ready = [n for n in remaining if all(p in placed for p in prereqs[n])]
        if not ready:
            raise ValueError(f"cycle detected: {' > '.join(find_cycle(prereqs, remaining))}")
        ordered += ready
        placed.update(ready)
        remaining = [n for n in remaining if n not in placed]

    # Keep `number` as an int so sorts stay numeric. `label` is the printed
    # form (`T1`). Mixing them would put T10 before T9.
    numbers = {name: i for i, name in enumerate(ordered, start=1)}
    labels = {name: f"T{numbers[name]}" for name in ordered}
    return {
        "tasks": [
            {
                "number": numbers[name],
                "label": labels[name],
                "id": name,
                "goal": slices_by_id[name].goal,
                "category": slices_by_id[name].category,
                "prereqs": sorted(prereqs[name], key=lambda p: numbers[p]),
                "dependents": sorted(dependents[name], key=lambda d: numbers[d]),
            }
            for name in ordered
        ],
        "numbers": numbers,
        "labels": labels,
        "goals": goal_order,
        "planner_edges": planner_edges,
        "cut_edges": cut_edges,
        "edges": all_edges,
    }


def find_cycle(prereqs: dict[str, list[str]], scope: list[str]) -> list[str]:
    """Return one cycle among the stuck tasks, written as prerequisite > dependent."""
    path: list[str] = []
    seen: set[str] = set()
    node = scope[0]
    while node not in seen:
        seen.add(node)
        path.append(node)
        candidates = [p for p in prereqs[node] if p in scope]
        if not candidates:
            return path[::-1]
        node = candidates[0]
    cycle = path[path.index(node) :] + [node]
    return cycle[::-1]


def _cell_edges(names: list[str], labels: dict[str, str]) -> str:
    return ", ".join(labels[n] for n in names) or "—"


def render_goals(dag: dict) -> str:
    """Print | Goal | Tasks | with at least one Task # per goal."""
    by_goal: dict[str, list[str]] = {goal: [] for goal in dag["goals"]}
    for task in dag["tasks"]:
        by_goal[task["goal"]].append(task["label"])
    lines = ["| Goal | Tasks |", "|---|---|"]
    for goal in dag["goals"]:
        lines.append(f"| {goal} | {', '.join(by_goal[goal])} |")
    return "\n".join(lines)


def render_table(dag: dict) -> str:
    """Print the tasks as an unfenced markdown table.

    Depends on answers "can this start?" and includes goal-cut edges. The
    plan is a static document, so the table carries no status column, and no
    reverse-edge column that could contradict Depends on.
    """
    labels = dag["labels"]
    lines = [
        "| Task # | Goal | Category | Task | Depends on | Success criterion |",
        "|---|---|---|---|---|---|",
    ]
    for task in dag["tasks"]:
        depends = _cell_edges(task["prereqs"], labels)
        lines.append(
            f"| {task['label']} | {task['goal']} | {task['category']} | {task['id']} "
            f"| {depends} | <observable check> |"
        )
    return "\n".join(lines)


def render_pairs(dag: dict) -> str:
    def block(title: str, edges: list[tuple[str, str]]) -> list[str]:
        if not edges:
            return [title, "", "(none)"]
        width = max(len(src) for src, _ in edges)
        lines = [title, "", "```"]
        lines += [f"{src.ljust(width)} > {dst}" for src, dst in edges]
        lines.append("```")
        return lines

    parts = block("Immediate dependencies (`prerequisite > dependent`):", dag["planner_edges"])
    if dag["cut_edges"]:
        parts += ["", *block("Goal-cut edges (generated; do not pass these back in):", dag["cut_edges"])]
    return "\n".join(parts)


def render_task_execution(dag: dict) -> list[str]:
    lines = [
        "| Task # | Executor | Rationale |",
        "|---|---|---|",
    ]
    for task in dag["tasks"]:
        lines.append(
            f"| {task['label']} | <main-agent or subagent> | <why this task is or is not delegated> |"
        )
    return lines


def render_task_bodies(dag: dict) -> list[str]:
    lines: list[str] = []
    for task in dag["tasks"]:
        if lines:
            lines.append("")
        lines += [
            f"### {task['label']} {task['id']}",
            "",
            "**Files**",
            "",
            "- <path in this task's category, or — for read-only work>",
            "",
            "**Consumes**",
            "",
            "- —",
            "",
            "**Produces**",
            "",
            "- —",
            "",
            "**Verify**",
            "",
            "- <command or check that proves the success criterion>",
        ]
    return lines


def render_scaffold(dag: dict, title: str) -> str:
    """Print a full plan document with every generated cell already filled."""
    return "\n".join(
        [
            f"# Execution Plan — {title}",
            "",
            "## Problem Statement",
            "",
            "<what is broken or missing today, and why changing it is worth the work>",
            "",
            "**Goals**",
            "",
            render_goals(dag),
            "",
            "**Non-goals** <!-- omit this heading and list unless the user named non-goals -->",
            "",
            "- <non-goal>",
            "",
            "**Constraints** <!-- omit this heading and list unless the spec or user named them -->",
            "",
            "- <constraint>",
            "",
            "## Task DAG",
            "",
            render_table(dag),
            "",
            "## Task Execution",
            "",
            *render_task_execution(dag),
            "",
            "## Tasks",
            "",
            *render_task_bodies(dag),
            "",
            "## Spec Sync",
            "",
            "<!-- If no spec sync slice: replace this table with one line saying no clause",
            "     changes, and why. Driven by must be a Task # on the DAG. -->",
            "",
            "| Clause | Document | Change | Driven by |",
            "|---|---|---|---|",
            "| <clause id or heading> | <product requirements / implementation guidelines> "
            "| <add / amend / remove> | <Task #> |",
            "",
            "## Execution Guidelines",
            "",
            "Do not start any task until `Confirm plan? [1. Yes / 2. No]` has been",
            "answered `1`. Wait for the answer. On `2`, revise the plan; start no task.",
            "",
            "If this plan has a spec sync task, show the `## Spec Sync` table and ask",
            "`Confirm spec update? [1. Yes / 2. No]` before any task starts. Wait for",
            "the answer. On `2`, drop that task, write one line here saying why, and",
            "re-run the tool so the numbering stays generated.",
            "",
            "Goals are serial. Within a goal, ready tasks with no edge and no",
            "overlapping files may run in parallel. Launch ready `subagent` tasks",
            "together. Keep integration and final synthesis on the main agent.",
            "",
            "On a wrong or missing edge, fix the pairs, re-run the tool, and replace",
            "the tables. Never patch numbering by hand.",
        ]
    )


def render_json(dag: dict) -> str:
    return json.dumps({"goals": dag["goals"], "tasks": dag["tasks"]}, indent=2)


RENDERERS = {
    "table": render_table,
    "pairs": render_pairs,
    "json": render_json,
    "goals": render_goals,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pairs", nargs="*", help="intra-goal pairs, 'prerequisite > dependent'")
    parser.add_argument(
        "--task",
        "--slice",
        action="append",
        default=[],
        dest="slices",
        help="a task 'goal:category:id' (category is code, config, docs, or assets)",
    )
    parser.add_argument(
        "--goal-order",
        action="append",
        default=[],
        dest="goal_order",
        help="serial goal ids, comma-separated; inferred from --task if omitted",
    )
    parser.add_argument(
        "--format",
        choices=["all", "scaffold", *RENDERERS],
        default="all",
        help="what to print (default: goals table, DAG table, and pairs). scaffold prints the full plan",
    )
    parser.add_argument("--title", default="<objective>", help="plan title, used only with --format scaffold")
    args = parser.parse_args()

    try:
        pairs = list(args.pairs)
        slices = [parse_slice(s) for s in args.slices]
        goal_order = parse_goal_order(args.goal_order)
        if not sys.stdin.isatty() and not pairs and not slices:
            payload = json.loads(sys.stdin.read() or "{}")
            slices += _slices_from_json_tasks(payload.get("tasks", []))
            pairs += [f"{src} > {dst}" for src, dst in payload.get("edges", [])]
            if not goal_order:
                raw_goals = payload.get("goals", [])
                if isinstance(raw_goals, list):
                    goal_order = [str(g) for g in raw_goals if g]
        edges = [parse_pair(raw) for raw in pairs]
        dag = build(edges, slices, goal_order)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.format == "scaffold":
        print(render_scaffold(dag, args.title))
        return 0

    if args.format != "all":
        print(RENDERERS[args.format](dag))
        return 0

    print(render_goals(dag))
    print()
    print(render_table(dag))
    print()
    print(render_pairs(dag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
