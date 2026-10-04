# Documentation writer MCP

This local stdio MCP server exposes one tool, `write_project_documentation`. It accepts a distilled
implementation brief, validates its workspace and document boundaries, and launches local Codex
with `gpt-6-sol` at medium reasoning effort. Codex may inspect the supplied evidence manifest and
edits only the named human-readable project documents.

The caller should provide:

- finalized changes, with abandoned approaches and debugging history removed;
- a summary of each changed system component;
- target document paths relative to the workspace;
- an evidence manifest whose `path` values are absolute file paths, plus each file's relevance and
  key facts;
- audience, desired reader outcome, constraints, validation checks, and known uncertainties when
  relevant.

The tool accepts one `brief` object with this shape:

```json
{
  "workspace_root": "/absolute/path/to/project",
  "objective": "Update the README and design spec for strict configuration parsing.",
  "target_documents": ["README.md", "docs/design.md"],
  "finalized_changes": ["Unknown configuration keys now fail validation."],
  "changed_components": [
    {
      "component": "configuration parser",
      "summary": "Validates all keys before constructing settings.",
      "reader_impact": "Readers need the new failure behavior and error format."
    }
  ],
  "evidence_manifest": [
    {
      "path": "/absolute/path/to/project/src/config.py",
      "relevance": "Implements validation and error construction.",
      "facts": ["Validation happens before settings construction."]
    }
  ],
  "audience": "project contributors",
  "desired_reader_outcome": "Configure the project and diagnose invalid keys.",
  "constraints": ["Use the term configuration key."],
  "validation": ["Check that both documents describe the same error behavior."],
  "uncertainties": [],
  "allow_create": false
}
```

Run `install-mcp.sh` from the repository root to install the runtime and register it with supported
clients. The server uses the existing local Codex login and does not require an API key.
