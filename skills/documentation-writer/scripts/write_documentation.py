#!/usr/bin/env python3
"""Launch a bounded Codex run for project documentation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

MODEL = "gpt-6-sol"
REASONING_EFFORT = "medium"
DOCUMENT_SUFFIXES = {".adoc", ".md", ".mdx", ".rst", ".txt"}
IGNORED_DIRECTORIES = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv", "node_modules"}
BUNDLED_CODEX_PATHS = (
    Path("/Applications/Codex.app/Contents/Resources/codex"),
    Path("/Applications/ChatGPT.app/Contents/Resources/codex"),
)


class DocumentationWriterError(RuntimeError):
    """Raised when a brief is invalid or a Codex run crosses its boundary."""


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DocumentationWriterError(f"{field} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, field: str, *, required: bool = False) -> list[str]:
    if value is None and not required:
        return []
    if not isinstance(value, list) or (required and not value):
        qualifier = "a non-empty" if required else "a"
        raise DocumentationWriterError(f"{field} must be {qualifier} list of strings")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(_string(item, f"{field}[{index}]"))
    return result


def _resolve_targets(root: Path, targets: Any, allow_create: bool) -> list[Path]:
    names = _string_list(targets, "target_documents", required=True)
    resolved: list[Path] = []
    for raw in names:
        candidate = Path(raw).expanduser()
        path = (candidate if candidate.is_absolute() else root / candidate).resolve()
        if not _within(path, root):
            raise DocumentationWriterError(f"target document is outside workspace_root: {raw}")
        if path.suffix.lower() not in DOCUMENT_SUFFIXES:
            raise DocumentationWriterError(f"target document is not a supported text format: {raw}")
        if not path.exists() and not allow_create:
            raise DocumentationWriterError(f"target document does not exist: {raw}")
        if path.exists() and not path.is_file():
            raise DocumentationWriterError(f"target document is not a file: {raw}")
        resolved.append(path)
    return resolved


def _components(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise DocumentationWriterError("changed_components must contain at least one component")
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise DocumentationWriterError(f"changed_components[{index}] must be an object")
        normalized.append(
            {
                "component": _string(item.get("component"), f"changed_components[{index}].component"),
                "summary": _string(item.get("summary"), f"changed_components[{index}].summary"),
                "reader_impact": str(item.get("reader_impact", "")).strip(),
            }
        )
    return normalized


def _manifest(root: Path, value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise DocumentationWriterError("evidence_manifest must contain at least one evidence file")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise DocumentationWriterError(f"evidence_manifest[{index}] must be an object")
        raw = _string(item.get("path"), f"evidence_manifest[{index}].path")
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            raise DocumentationWriterError(f"evidence_manifest[{index}].path must be absolute: {raw}")
        path = candidate.resolve()
        if not _within(path, root):
            raise DocumentationWriterError(f"evidence path is outside workspace_root: {raw}")
        if not path.is_file():
            raise DocumentationWriterError(f"evidence path is not a readable file: {raw}")
        normalized.append(
            {
                "path": str(path),
                "relevance": _string(item.get("relevance"), f"evidence_manifest[{index}].relevance"),
                "facts": _string_list(item.get("facts"), f"evidence_manifest[{index}].facts", required=True),
            }
        )
    return normalized


def normalize_brief(raw: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    """Validate the caller's final-state context and normalize its paths."""
    if not isinstance(raw, dict):
        raise DocumentationWriterError("brief must be a JSON object")
    root = Path(_string(raw.get("workspace_root"), "workspace_root")).expanduser().resolve()
    if not root.is_dir():
        raise DocumentationWriterError(f"workspace_root is not a directory: {root}")
    allow_create = raw.get("allow_create", False)
    if not isinstance(allow_create, bool):
        raise DocumentationWriterError("allow_create must be true or false")
    targets = _resolve_targets(root, raw.get("target_documents"), allow_create)
    brief = {
        "objective": _string(raw.get("objective"), "objective"),
        "audience": _string(raw.get("audience", "project contributors"), "audience"),
        "desired_reader_outcome": _string(
            raw.get("desired_reader_outcome", "Understand the current system and use it correctly."),
            "desired_reader_outcome",
        ),
        "target_documents": [path.relative_to(root).as_posix() for path in targets],
        "finalized_changes": _string_list(raw.get("finalized_changes"), "finalized_changes", required=True),
        "changed_components": _components(raw.get("changed_components")),
        "evidence_manifest": _manifest(root, raw.get("evidence_manifest")),
        "constraints": _string_list(raw.get("constraints"), "constraints"),
        "validation": _string_list(raw.get("validation"), "validation"),
        "uncertainties": _string_list(raw.get("uncertainties"), "uncertainties"),
        "allow_create": allow_create,
    }
    return root, brief


def build_prompt(brief: dict[str, Any]) -> str:
    payload = json.dumps(brief, indent=2, ensure_ascii=False)
    return f"""You are a project-documentation writing expert.

Edit the named project documents in clear, natural English. Accurately explain the finalized
implementation, and optimize sentence structure, information order, terminology, and word choice
for the stated audience.

Documentation brief:
```json
{payload}
```

Rules:
- Treat finalized_changes and changed_components as the authoritative outcome. Do not document
  abandoned approaches, debugging history, or intermediary discussion cycles.
- Inspect files in evidence_manifest selectively when the brief needs more detail. Do not perform
  an unfocused repository scan.
- Edit only target_documents. Never edit source code, tests, configuration, inline comments, or
  docstrings. Create a target only when allow_create is true.
- Preserve established terminology, document structure, and useful existing content.
- Write for a human reader. Prefer direct sentences, concrete nouns, and explicit relationships.
  Remove repetition, filler, vague claims, and irrelevant implementation trivia.
- Do not invent behavior. Report unresolved uncertainty instead of presenting it as fact.
- Run only relevant validation checks listed in the brief.

When finished, report which target documents changed, what you clarified, and any unresolved
documentation uncertainty. Do not paste the full documents into the report.
"""


def _snapshot(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for current, directories, files in os.walk(root):
        directories[:] = [name for name in directories if name not in IGNORED_DIRECTORIES]
        base = Path(current)
        for name in files:
            path = base / name
            if path.is_symlink() or not path.is_file():
                continue
            try:
                snapshot[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
    return snapshot


def _codex_executable() -> str:
    discovered = shutil.which("codex")
    if discovered:
        return discovered
    for candidate in BUNDLED_CODEX_PATHS:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    raise DocumentationWriterError(
        "codex executable was not found on PATH or in the Codex/ChatGPT macOS app bundle"
    )


def write_project_documentation(
    raw_brief: dict[str, Any],
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    root, brief = normalize_brief(raw_brief)
    before = _snapshot(root)
    with tempfile.TemporaryDirectory(prefix="documentation-writer-") as temporary:
        final_message = Path(temporary) / "final.txt"
        command = [
            _codex_executable(), "exec", "--ephemeral", "--ignore-user-config", "--color", "never",
            "--sandbox", "workspace-write", "--model", MODEL, "--config",
            f'model_reasoning_effort="{REASONING_EFFORT}"', "--cd", str(root),
            "--output-last-message", str(final_message), "-",
        ]
        try:
            completed = runner(
                command, input=build_prompt(brief), capture_output=True, text=True,
                timeout=1200, cwd=root,
            )
        except subprocess.TimeoutExpired as exc:
            raise DocumentationWriterError("Codex documentation run exceeded 20 minutes") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[-4000:]
            raise DocumentationWriterError(f"Codex documentation run failed: {detail}")
        report = final_message.read_text().strip() if final_message.exists() else completed.stdout.strip()

    after = _snapshot(root)
    changed = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
    allowed = set(brief["target_documents"])
    unexpected = [path for path in changed if path not in allowed]
    if unexpected:
        raise DocumentationWriterError(
            "Codex changed files outside target_documents: " + ", ".join(unexpected)
        )
    return {
        "status": "completed",
        "model": MODEL,
        "reasoning_effort": REASONING_EFFORT,
        "changed_documents": [path for path in changed if path in allowed],
        "report": report,
    }


def _load_brief(source: str) -> dict[str, Any]:
    try:
        content = sys.stdin.read() if source == "-" else Path(source).expanduser().read_text()
        value = json.loads(content)
    except (OSError, json.JSONDecodeError) as exc:
        raise DocumentationWriterError(f"could not read brief JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise DocumentationWriterError("brief must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Delegate a bounded documentation update to Codex.")
    parser.add_argument("--brief", default="-", help="JSON brief path, or - for standard input")
    parser.add_argument("--validate-only", action="store_true", help="validate and normalize without running Codex")
    args = parser.parse_args()
    try:
        raw = _load_brief(args.brief)
        if args.validate_only:
            root, brief = normalize_brief(raw)
            result: dict[str, Any] = {"status": "valid", "workspace_root": str(root), "brief": brief}
        else:
            result = write_project_documentation(raw)
    except DocumentationWriterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
