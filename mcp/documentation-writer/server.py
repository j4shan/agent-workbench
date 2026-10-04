#!/usr/bin/env python3
"""stdio MCP server exposing the project documentation writer."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from writer import write_project_documentation as run_writer

server = FastMCP("documentation-writer")


class ComponentSummary(BaseModel):
    """Final state of one changed system component."""

    component: str = Field(description="Stable component name or responsibility.")
    summary: str = Field(description="What the component does now and how it changed.")
    reader_impact: str = Field(
        default="", description="What a documentation reader must understand or do differently."
    )


class EvidenceFile(BaseModel):
    """A repository file the writer may inspect for supporting detail."""

    path: str = Field(description="Fully qualified path to one evidence file in the workspace.")
    relevance: str = Field(description="Why this file is useful for the documentation update.")
    facts: list[str] = Field(description="Finalized facts this file supports.")


class DocumentationBrief(BaseModel):
    """Distilled final-state context for one documentation update."""

    workspace_root: str = Field(description="Fully qualified root of the project to document.")
    objective: str = Field(description="Specific documentation outcome to achieve.")
    target_documents: list[str] = Field(
        min_length=1, description="Project-relative human-readable files Codex may edit."
    )
    finalized_changes: list[str] = Field(
        min_length=1, description="Completed behavior and decisions, excluding discarded approaches."
    )
    changed_components: list[ComponentSummary] = Field(
        min_length=1, description="Final-state summary of every affected system component."
    )
    evidence_manifest: list[EvidenceFile] = Field(
        min_length=1, description="Files Codex may inspect when the distilled facts need expansion."
    )
    audience: str = Field(default="project contributors", description="Primary documentation readers.")
    desired_reader_outcome: str = Field(
        default="Understand the current system and use it correctly.",
        description="What readers should know or be able to do after reading.",
    )
    constraints: list[str] = Field(default_factory=list, description="Terminology and scope constraints.")
    validation: list[str] = Field(default_factory=list, description="Relevant documentation checks.")
    uncertainties: list[str] = Field(
        default_factory=list, description="Known gaps Codex must not silently resolve as facts."
    )
    allow_create: bool = Field(
        default=False, description="Whether missing target documents may be created."
    )


@server.tool()
def write_project_documentation(brief: DocumentationBrief) -> dict:
    """Write or revise project documentation from a distilled implementation brief.

    Send finalized outcomes rather than discussion history. Summarize each changed component and
    provide absolute evidence file paths with their relevance and key facts. The tool may inspect
    those files when it needs detail, but it edits only the target documents. It uses local Codex
    with gpt-6-sol and medium reasoning to produce clear, human-readable English.
    """
    values = brief.model_dump()
    return run_writer(
        workspace_root=values["workspace_root"],
        objective=values["objective"],
        target_documents=values["target_documents"],
        finalized_changes=values["finalized_changes"],
        changed_components=values["changed_components"],
        evidence_manifest=values["evidence_manifest"],
        audience=values["audience"],
        desired_reader_outcome=values["desired_reader_outcome"],
        constraints=values["constraints"],
        validation=values["validation"],
        uncertainties=values["uncertainties"],
        allow_create=values["allow_create"],
    )


if __name__ == "__main__":
    server.run(transport="stdio")
