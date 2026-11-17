#!/usr/bin/env python3
"""Load the user-configured reviewer and replace this process with read-only gpt-exec."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import NoReturn


MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]*\Z")
EFFORT = re.compile(r"[a-z][a-z0-9-]*\Z")


def load_review_settings(
    model: str | None = None, reasoning_effort: str | None = None,
) -> tuple[str, str]:
    """Read one JSON snapshot, validate the pair, and apply per-call overrides."""
    directory = Path(os.environ.get(
        "SUBAGENT_MODELS_DIR", str(Path.home() / "Library/Application Support/subagent-models"),
    ))
    if not directory.is_absolute():
        raise ValueError("SUBAGENT_MODELS_DIR must be a nonempty absolute directory")
    path = directory / "code-reviewer.json"
    try:
        pair = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"reviewer configuration is missing: {path}; configure the role explicitly") from None
    except (json.JSONDecodeError, UnicodeError):
        raise ValueError(f"reviewer configuration is not valid UTF-8 JSON: {path}") from None
    if not isinstance(pair, list) or len(pair) != 2 or any(not isinstance(value, str) for value in pair):
        raise ValueError("reviewer configuration must contain exactly two strings: [model, effort]")
    if not MODEL.fullmatch(pair[0]) or not EFFORT.fullmatch(pair[1]):
        raise ValueError("reviewer configuration contains invalid model or effort identifiers")
    selected_model = pair[0] if model is None else model
    selected_effort = pair[1] if reasoning_effort is None else reasoning_effort
    if not MODEL.fullmatch(selected_model) or not EFFORT.fullmatch(selected_effort):
        raise ValueError("invalid per-call model or effort identifier")
    return selected_model, selected_effort


def exec_review(
    project: Path,
    prompt_file: Path,
    *,
    model: str | None = None,
    reasoning_effort: str | None = None,
    gpt_exec: Path | None = None,
    json_output: bool = False,
    output_last_message: Path | None = None,
) -> NoReturn:
    """Preserve gpt-exec's stdin contract, process identity, exit status, and signals."""
    model, effort = load_review_settings(model, reasoning_effort)
    executable = gpt_exec if gpt_exec is not None else Path.home() / ".local/bin/gpt-exec"
    if not executable.is_absolute():
        raise ValueError("--gpt-exec must be an absolute executable path")
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ValueError(f"gpt-exec is missing or not executable: {executable}; install the shared tool explicitly")
    args = [str(executable), "--model", model, "--reasoning-effort", effort,
            "--sandbox", "read-only", "--project", str(project), "--prompt-file", str(prompt_file)]
    if json_output:
        args.append("--json")
    if output_last_message is not None:
        args.extend(["--output-last-message", str(output_last_message)])
    os.execv(str(executable), args)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--model", help="explicit user override for this call")
    parser.add_argument("--reasoning-effort", help="explicit user override for this call")
    parser.add_argument("--gpt-exec", type=Path, help="absolute path when the shared tool is installed elsewhere")
    parser.add_argument("--json", dest="json_output", action="store_true")
    parser.add_argument("--output-last-message", type=Path)
    args = parser.parse_args()
    try:
        exec_review(**vars(args))
    except (OSError, ValueError) as error:
        print(f"review: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
