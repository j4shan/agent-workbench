# Working in this repository

Keep reusable skills, shared tools, and their documentation organized as follows.

## Project structure

| Path | Purpose |
| --- | --- |
| `skills/<name>/` | One skill per directory, with `SKILL.md` and optional `scripts/`, `references/`, and `assets/`. |
| `tools/` | Shared commands and scripts used by multiple skills or directly from the shell. |
| `instructions/` | Client rule files. |
| `docs/` | Design proposals and other project documentation. |
| `README.md` | Project overview, setup, and usage. |
| `install.sh`, `install.yaml` | Installation logic and inclusion settings. |

Create directories when their first file is needed.

## Naming and placement

- Use `skills/` and `tools/` as directory prefixes. No additional name prefix is required.
- Use lowercase kebab-case for new skill directories and shared tool names.
- Match each skill's frontmatter `name` to its directory name.
- Keep helpers used by only one skill in that skill's `scripts/` directory.
- Preserve existing names unless a rename is requested.

## Authoritative references

Use the standard for the skill format and the relevant vendor guide for client-specific behavior.

| Reference | Use for |
| --- | --- |
| [Agent Skills specification](https://agentskills.io/specification) | Skill structure, frontmatter, and naming. |
| [Claude skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | Writing and validating Claude skills. |
| [OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills) | Creating and using skills with OpenAI clients. |
