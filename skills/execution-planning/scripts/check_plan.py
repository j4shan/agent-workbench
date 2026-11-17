#!/usr/bin/env python3
"""Validate an execution plan against the plan document contract.

Print one line per violation and exit 1, or print nothing and exit 0. The
checker reads the document only. It cannot judge whether a success criterion is
observable; a person does that.

The strongest check rebuilds the graph: it takes the tasks and the intra-goal
edges as the table states them, re-runs the generator, and compares. Numbering
or edges patched by hand fail here.

Usage:
    check_plan.py <plan file>
    check_plan.py -                 # read the plan on stdin
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import plan_doc  # noqa: E402
from task_dag import Slice, build  # noqa: E402

DAG_HEADERS = ["Task #", "Goal", "Category", "Task", "Depends on", "Success criterion"]
GOALS_HEADERS = ["Goal", "Tasks"]

REQUIRED_SECTIONS = [
    "Problem Statement",
    "Task DAG",
    "Tasks",
    "Execution Guidelines",
]

BODY_FIELDS = ["Files", "Consumes", "Produces", "Verify"]
EMPTY = {"", "—", "-", "–"}

CONFIG_NAMES = {
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "requirements.txt",
    "pyproject.toml", "setup.py", "setup.cfg", "makefile", "dockerfile", "install.yaml",
    "install.sh", "tsconfig.json", ".gitignore",
}
CODE_SUFFIXES = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".c", ".h", ".cc",
    ".cpp", ".hpp", ".cs", ".kt", ".swift", ".sh", ".sql",
}
ASSET_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".woff", ".woff2", ".ttf",
    ".otf", ".mp3", ".mp4", ".pdf", ".drawio",
}


def path_text(entry: str) -> str:
    """Read a Files entry, preserving spaces inside a backtick-quoted path."""
    text = entry.lstrip("-* ").strip()
    if text.startswith("`"):
        return text[1:].split("`", 1)[0]
    return text.split(" (")[0].split(", ")[0].strip()


def classify(path: str) -> str | None:
    """Return the category a path belongs to, or None when it is not clear.

    Follows the tie-breaks the skill states. Returns None rather than guessing,
    so an unrecognised path never produces a finding.
    """
    clean = path_text(path)
    if not clean:
        return None
    lower = clean.lower()
    name = lower.rsplit("/", 1)[-1]
    suffix = "." + name.rsplit(".", 1)[-1] if "." in name else ""

    if name in CONFIG_NAMES or lower.startswith(".github/") or "/.github/" in lower:
        return "config"
    if name.startswith("test_") or name.endswith("_test.py") or ".test." in name:
        return "code"
    if lower.startswith("tests/") or "/tests/" in lower or "/fixtures/" in lower:
        return "code"
    if suffix in ASSET_SUFFIXES:
        return "assets"
    if suffix in CODE_SUFFIXES:
        return "code"
    if suffix in {".md", ".mdc", ".rst", ".txt"}:
        return "docs"
    if suffix in {".yaml", ".yml", ".toml", ".ini", ".cfg"}:
        return "config"
    return None


def is_test_path(path: str) -> bool:
    clean = path_text(path)
    lower = clean.lower()
    name = lower.rsplit("/", 1)[-1]
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or ".test." in name
        or lower.startswith("tests/")
        or "/tests/" in lower
        or "/fixtures/" in lower
    )


class Report:
    def __init__(self) -> None:
        self.findings: list[tuple[int, str]] = []

    def add(self, line: int, message: str) -> None:
        self.findings.append((line, message))


def check_sections(doc: plan_doc.PlanDoc, report: Report) -> None:
    present = [s.title for s in doc.sections]
    for title in REQUIRED_SECTIONS:
        if title not in present:
            report.add(0, f"missing required section '## {title}'")
    ordered = [t for t in present if t in REQUIRED_SECTIONS]
    expected = [t for t in REQUIRED_SECTIONS if t in ordered]
    if ordered != expected:
        report.add(0, f"sections out of contract order: {', '.join(ordered)}")


def check_placeholders(doc: plan_doc.PlanDoc, report: Report) -> None:
    for i, raw in enumerate(doc.structure, start=1):
        if plan_doc.SCAFFOLD_COMMENT.search(raw):
            report.add(i, "scaffold comment left in the plan")
        stripped = plan_doc.SCAFFOLD_COMMENT.sub("", raw)
        for hit in plan_doc.PLACEHOLDER.findall(stripped):
            if hit.startswith("</") or re.fullmatch(r"<[a-z]+>", hit):
                continue
            report.add(i, f"unfilled placeholder {hit}")


def rebuild(dag: plan_doc.Table, report: Report) -> dict | None:
    """Re-run the generator on what the table states, and compare."""
    numbers = [plan_doc.task_number(row["Task #"]) for row in dag.rows]
    if numbers != list(range(1, len(numbers) + 1)):
        report.add(dag.line, f"Task # column is not T1..T{len(numbers)} in order")
        return None

    slices = [Slice(row["Task"].strip(), row["Goal"].strip(), row["Category"].strip()) for row in dag.rows]
    goal_order = list(dict.fromkeys(task.goal for task in slices))
    by_label = {row["Task #"].strip(): row["Task"].strip() for row in dag.rows}
    intra: list[tuple[str, str]] = []
    goal_of = {s.id: s.goal for s in slices}
    for row, line in zip(dag.rows, dag.row_lines):
        target = row["Task"].strip()
        for ref in plan_doc.split_refs(row["Depends on"]):
            if ref not in by_label:
                report.add(line, f"Depends on names '{ref}', which is not a Task # in this plan")
                return None
            source = by_label[ref]
            if goal_of[source] == goal_of[target]:
                intra.append((source, target))

    try:
        return build(intra, slices, goal_order)
    except ValueError as exc:
        report.add(dag.line, f"the DAG table does not rebuild: {exc}")
        return None


def check_dag(doc: plan_doc.PlanDoc, report: Report) -> plan_doc.Table | None:
    tables = doc.tables.get("Task DAG", [])
    if not tables:
        report.add(0, "## Task DAG has no table")
        return None
    dag = tables[0]
    if dag.headers != DAG_HEADERS:
        report.add(dag.line, f"Task DAG columns must be {' | '.join(DAG_HEADERS)}")
        return None
    if not dag.rows:
        report.add(dag.line, "Task DAG has no rows")
        return None

    for row, line in zip(dag.rows, dag.row_lines):
        if row["Success criterion"].strip() in EMPTY:
            report.add(line, f"{row['Task #'].strip()} has no success criterion")

    rebuilt = rebuild(dag, report)
    if rebuilt is None:
        return dag

    expected_rows = {
        task["label"]: (task["goal"], task["category"], task["id"],
                        [rebuilt["labels"][p] for p in task["prereqs"]])
        for task in rebuilt["tasks"]
    }
    for row, line in zip(dag.rows, dag.row_lines):
        label = row["Task #"].strip()
        want = expected_rows.get(label)
        if want is None:
            report.add(line, f"{label} is not in the rebuilt graph")
            continue
        got_deps = plan_doc.split_refs(row["Depends on"])
        if got_deps != want[3]:
            shown = ", ".join(want[3]) or "—"
            report.add(line, f"{label} Depends on should be '{shown}'; re-run the tool")
        if (row["Goal"].strip(), row["Category"].strip(), row["Task"].strip()) != want[:3]:
            report.add(line, f"{label} does not match the rebuilt graph; re-run the tool")
    return dag


def check_goals(doc: plan_doc.PlanDoc, dag: plan_doc.Table, report: Report) -> None:
    goals = doc.table_with_headers("Problem Statement", GOALS_HEADERS)
    if goals is None:
        report.add(0, "## Problem Statement has no | Goal | Tasks | table")
        return
    by_goal: dict[str, list[str]] = {}
    order: list[str] = []
    for row in dag.rows:
        goal = row["Goal"].strip()
        if goal not in by_goal:
            by_goal[goal] = []
            order.append(goal)
        by_goal[goal].append(row["Task #"].strip())

    listed = [row["Goal"].strip() for row in goals.rows]
    if listed != order:
        report.add(goals.line, f"Goals order {listed} does not match the DAG order {order}")
    for row, line in zip(goals.rows, goals.row_lines):
        goal = row["Goal"].strip()
        cell = plan_doc.split_refs(row["Tasks"])
        if not cell:
            report.add(line, f"goal '{goal}' has a blank Tasks cell")
            continue
        if goal in by_goal and cell != by_goal[goal]:
            report.add(line, f"goal '{goal}' lists {cell}; the DAG has {by_goal[goal]}")


def check_bodies(doc: plan_doc.PlanDoc, dag: plan_doc.Table, report: Report) -> None:
    expected = [(row["Task #"].strip(), row["Task"].strip()) for row in dag.rows]
    found = [(body.label, body.id) for body in doc.task_bodies]
    if found != expected:
        report.add(0, f"## Tasks holds {found}; the DAG has {expected}")

    category_of = {row["Task #"].strip(): row["Category"].strip() for row in dag.rows}
    paths_by_label: dict[str, list[str]] = {}
    owner_by_path: dict[str, str] = {}
    for body in doc.task_bodies:
        for name in BODY_FIELDS:
            if name not in body.fields:
                report.add(body.line, f"{body.label} body has no **{name}**")
                continue
            filled = [v for v in body.fields[name] if v.strip("-* ").strip()]
            if not filled:
                report.add(body.line, f"{body.label} **{name}** is empty")
            elif name == "Verify" and not [
                v for v in filled if v.strip("-* ").strip() not in EMPTY
            ]:
                # Files, Consumes, and Produces may legitimately be the em dash;
                # Verify may not.
                report.add(body.line, f"{body.label} **{name}** is empty")
        want = category_of.get(body.label)
        paths_by_label[body.label] = []
        for entry in body.fields.get("Files", []):
            path = path_text(entry)
            if path in EMPTY:
                continue
            paths_by_label[body.label].append(path)
            previous = owner_by_path.get(path)
            if previous and previous != body.label:
                report.add(body.line, f"{path} is owned by both {previous} and {body.label}")
            owner_by_path[path] = body.label
            got = classify(path)
            if want and got and got != want:
                report.add(body.line, f"{body.label} is a {want} task but Files names '{path}' ({got})")

    code_by_goal: dict[str, list[str]] = {}
    for row in dag.rows:
        if row["Category"].strip() == "code":
            code_by_goal.setdefault(row["Goal"].strip(), []).append(row["Task #"].strip())
    body_line = {body.label: body.line for body in doc.task_bodies}
    for goal, labels in code_by_goal.items():
        if len(labels) != 2:
            continue
        roles: list[str] = []
        for label in labels:
            paths = [p for p in paths_by_label.get(label, []) if classify(p) == "code"]
            flags = [is_test_path(p) for p in paths]
            if flags and all(flags):
                roles.append("tests")
            elif flags and not any(flags):
                roles.append("source")
            else:
                roles.append("mixed")
        if sorted(roles) != ["source", "tests"]:
            report.add(
                body_line.get(labels[1], 0),
                f"goal '{goal}' has two code tasks; one must own production source and one tests",
            )


def validate_plan(path: str | Path) -> list[tuple[int, str]]:
    """Return sorted (source line, message) findings without printing or editing files."""
    doc = plan_doc.load(path)
    report = Report()
    check_sections(doc, report)
    check_placeholders(doc, report)
    dag = check_dag(doc, report)
    if dag is not None:
        check_goals(doc, dag, report)
        check_bodies(doc, dag, report)
    return sorted(report.findings)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan", help="path to the plan file, or - for stdin")
    args = parser.parse_args()

    try:
        findings = validate_plan(args.plan)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for line, message in findings:
        where = f"{args.plan}:{line}" if line else args.plan
        print(f"{where}: {message}")
    return int(bool(findings))


if __name__ == "__main__":
    sys.exit(main())
