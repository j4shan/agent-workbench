"""Validated Codex launcher for the documentation-writer MCP server."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

MODEL = "gpt-6-sol"
REASONING_EFFORT = "medium"
DOCUMENT_SUFFIXES = {".adoc", ".md", ".mdx", ".rst", ".txt"}
IGNORED_DIRECTORIES = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv", "node_modules"}


class DocumentationWriterError(RuntimeError):
    """Raised when a brief is invalid or the Codex run is unsafe."""


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _resolve_targets(root: Path, targets: list[str], allow_create: bool) -> list[Path]:
    if not targets:
        raise DocumentationWriterError("target_documents must name at least one document")

    resolved: list[Path] = []
    for raw in targets:
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


def _validate_manifest(root: Path, manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not manifest:
        raise DocumentationWriterError("evidence_manifest must contain at least one evidence file")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(manifest):
        raw = item.get("path", "")
        if not raw:
            raise DocumentationWriterError(f"evidence_manifest[{index}] has no path")
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            raise DocumentationWriterError(
                f"evidence_manifest[{index}].path must be fully qualified: {raw}"
            )
        path = candidate.resolve()
        if not _within(path, root):
            raise DocumentationWriterError(f"evidence path is outside workspace_root: {raw}")
        if not path.is_file():
            raise DocumentationWriterError(f"evidence path is not a readable file: {raw}")
        normalized.append(
            {
                "path": str(path),
                "relevance": item.get("relevance", ""),
                "facts": item.get("facts", []),
            }
        )
    return normalized


def build_prompt(brief: dict[str, Any]) -> str:
    """Build the stable editorial contract passed to Codex."""
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
- Inspect files in evidence_manifest selectively when the brief does not contain enough detail.
  Use the manifest descriptions to decide what to open. Do not perform an unfocused repository scan.
- Edit only target_documents. Never edit source code, tests, configuration, inline comments, or
  docstrings. Create a target only when allow_create is true.
- Preserve established project terminology, document structure, and useful existing content.
- Write for a human reader. Prefer direct sentences, concrete nouns, and explicit relationships.
  Remove repetition, filler, vague claims, and implementation trivia that does not help the reader.
- Do not invent behavior. Surface unresolved uncertainty in your final report instead of presenting
  it as fact.
- Run only the validation checks listed in the brief when they are relevant to documentation.

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
            relative = path.relative_to(root).as_posix()
            try:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
            snapshot[relative] = digest
    return snapshot


def _changed_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))


def write_project_documentation(
    *,
    workspace_root: str,
    objective: str,
    target_documents: list[str],
    finalized_changes: list[str],
    changed_components: list[dict[str, Any]],
    evidence_manifest: list[dict[str, Any]],
    audience: str = "project contributors",
    desired_reader_outcome: str = "Understand the current system and use it correctly.",
    constraints: list[str] | None = None,
    validation: list[str] | None = None,
    uncertainties: list[str] | None = None,
    allow_create: bool = False,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """Validate a documentation brief, run Codex, and report the bounded changes."""
    root = Path(workspace_root).expanduser().resolve()
    if not root.is_dir():
        raise DocumentationWriterError(f"workspace_root is not a directory: {workspace_root}")
    if not objective.strip():
        raise DocumentationWriterError("objective must not be empty")
    if not finalized_changes:
        raise DocumentationWriterError("finalized_changes must contain at least one completed change")
    if not changed_components:
        raise DocumentationWriterError("changed_components must summarize at least one component")

    targets = _resolve_targets(root, target_documents, allow_create)
    manifest = _validate_manifest(root, evidence_manifest)
    relative_targets = [path.relative_to(root).as_posix() for path in targets]
    brief = {
        "objective": objective,
        "audience": audience,
        "desired_reader_outcome": desired_reader_outcome,
        "target_documents": relative_targets,
        "finalized_changes": finalized_changes,
        "changed_components": changed_components,
        "evidence_manifest": manifest,
        "constraints": constraints or [],
        "validation": validation or [],
        "uncertainties": uncertainties or [],
        "allow_create": allow_create,
    }

    before = _snapshot(root)
    with tempfile.TemporaryDirectory(prefix="documentation-writer-") as temporary:
        final_message = Path(temporary) / "final.txt"
        command = [
            "codex", "exec", "--ephemeral", "--ignore-user-config", "--color", "never",
            "--sandbox", "workspace-write", "--model", MODEL, "--config",
            f'model_reasoning_effort="{REASONING_EFFORT}"', "--cd", str(root),
            "--output-last-message", str(final_message), "-",
        ]
        try:
            completed = runner(
                command, input=build_prompt(brief), capture_output=True, text=True,
                timeout=1200, cwd=root,
            )
        except FileNotFoundError as exc:
            raise DocumentationWriterError("codex executable was not found on PATH") from exc
        except subprocess.TimeoutExpired as exc:
            raise DocumentationWriterError("Codex documentation run exceeded 20 minutes") from exc

        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[-4000:]
            raise DocumentationWriterError(f"Codex documentation run failed: {detail}")
        report = final_message.read_text().strip() if final_message.exists() else completed.stdout.strip()

    changed = _changed_paths(before, _snapshot(root))
    allowed = set(relative_targets)
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
