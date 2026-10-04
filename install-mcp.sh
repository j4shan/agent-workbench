#!/usr/bin/env bash
# Install and register the documentation-writer MCP server on macOS.

set -euo pipefail

source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
server_source="$source_root/mcp/documentation-writer"
server_name="documentation-writer"

usage() {
    cat <<'EOF'
Usage:
  install-mcp.sh [--scope project] [--client all|codex,claude,cursor] <project-dir>
  install-mcp.sh --scope user [--client all|codex,claude,cursor]

Install the documentation-writer stdio MCP server and register it with compatible clients.

  --scope project|user   registration scope (default: project)
  --client <list>        clients to configure (default: all)
  <project-dir>          target project root (required for project scope)
  -h, --help             show this message

Project scope installs the runtime under <project>/.agents/mcp/documentation-writer.
User scope installs it under ~/Library/Application Support/agent-workbench/mcp/.
EOF
}

die() {
    echo "error: $*" >&2
    exit 1
}

[[ "$(uname -s)" == "Darwin" ]] || die "install-mcp.sh supports macOS only"

scope=project
clients=all
positionals=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --scope)
            [[ $# -ge 2 ]] || die "--scope requires project or user"
            scope="$2"; shift 2 ;;
        --scope=*) scope="${1#--scope=}"; shift ;;
        --client)
            [[ $# -ge 2 ]] || die "--client requires a client list"
            clients="$2"; shift 2 ;;
        --client=*) clients="${1#--client=}"; shift ;;
        --) shift; positionals+=("$@"); break ;;
        -*) die "unknown argument '$1'" ;;
        *) positionals+=("$1"); shift ;;
    esac
done

case "$scope" in project|user) ;; *) die "--scope must be project or user" ;; esac
[[ -d "$server_source" ]] || die "missing server source: $server_source"
command -v codex >/dev/null 2>&1 || die "codex is required and must be on PATH"
bootstrap_python=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1 \
        && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
        bootstrap_python="$(command -v "$candidate")"
        break
    fi
done
[[ -n "$bootstrap_python" ]] || die "Python 3.10 or newer is required"

compact_clients="${clients//[[:space:]]/}"
[[ -n "$compact_clients" ]] || die "--client list must not be empty"
if [[ "$compact_clients" == ,* || "$compact_clients" == *, || "$compact_clients" == *,,* ]]; then
    die "--client contains an empty name"
fi
normalized_clients=",$compact_clients,"
if [[ "$compact_clients" == all ]]; then
    normalized_clients=",codex,claude,cursor,"
fi
for client in ${compact_clients//,/ }; do
    [[ "$client" == codex || "$client" == claude || "$client" == cursor \
        || ( "$client" == all && "$compact_clients" == all ) ]] \
        || die "unsupported client '$client'"
done
has_client() { [[ "$normalized_clients" == *",$1,"* ]]; }

if [[ "$scope" == project ]]; then
    [[ ${#positionals[@]} -eq 1 ]] || die "project scope requires exactly one project directory"
    [[ -d "${positionals[0]}" ]] || die "not a directory: ${positionals[0]}"
    project_root="$(cd "${positionals[0]}" && pwd)"
    [[ "$project_root" != "$source_root" ]] || die "refuse to install into agent-workbench itself"
    install_root="$project_root/.agents/mcp/$server_name"
else
    [[ ${#positionals[@]} -eq 0 ]] || die "user scope takes no project directory"
    user_home="$HOME"
    install_root="$user_home/Library/Application Support/agent-workbench/mcp/$server_name"
fi

mkdir -p "$install_root"
cp "$server_source/server.py" "$install_root/server.py"
cp "$server_source/writer.py" "$install_root/writer.py"
cp "$server_source/requirements.txt" "$install_root/requirements.txt"
cp "$server_source/README.md" "$install_root/README.md"

if [[ ! -x "$install_root/.venv/bin/python" ]]; then
    "$bootstrap_python" -m venv "$install_root/.venv"
fi
"$install_root/.venv/bin/python" -m pip install --disable-pip-version-check \
    --requirement "$install_root/requirements.txt"

server_python="$install_root/.venv/bin/python"
server_script="$install_root/server.py"

update_json_config() {
    local config_path="$1"
    mkdir -p "$(dirname "$config_path")"
    "$bootstrap_python" - "$config_path" "$server_name" "$server_python" "$server_script" <<'PY'
import json
import sys
from pathlib import Path

path, name, command, script = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
if path.exists():
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: invalid JSON in {path}: {exc}")
else:
    data = {}
servers = data.setdefault("mcpServers", {})
if not isinstance(servers, dict):
    raise SystemExit(f"error: mcpServers is not an object in {path}")
servers[name] = {"command": command, "args": [script]}
path.write_text(json.dumps(data, indent=2) + "\n")
PY
}

update_codex_config() {
    local config_path="$1"
    mkdir -p "$(dirname "$config_path")"
    "$bootstrap_python" - "$config_path" "$server_name" "$server_python" "$server_script" <<'PY'
import json
import re
import sys
from pathlib import Path

path, name, command, script = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
start = f"# >>> agent-workbench {name} >>>"
end = f"# <<< agent-workbench {name} <<<"
text = path.read_text() if path.exists() else ""
managed = re.compile(rf"(?ms)^\s*{re.escape(start)}.*?^\s*{re.escape(end)}\s*\n?")
base = managed.sub("", text).rstrip()
unmanaged_table = re.compile(
    rf'(?m)^\s*\[mcp_servers\.(?:{re.escape(name)}|"{re.escape(name)}")\]\s*$'
)
if unmanaged_table.search(base):
    raise SystemExit(
        f"error: {path} already has unmanaged mcp_servers.{name}; remove or rename it first"
    )
block = "\n".join([
    start,
    f"[mcp_servers.{name}]",
    f"command = {json.dumps(command)}",
    f"args = [{json.dumps(script)}]",
    end,
])
path.write_text((base + "\n\n" if base else "") + block + "\n")
PY
}

if [[ "$scope" == project ]]; then
    if has_client codex; then update_codex_config "$project_root/.codex/config.toml"; fi
    if has_client claude; then update_json_config "$project_root/.mcp.json"; fi
    if has_client cursor; then update_json_config "$project_root/.cursor/mcp.json"; fi
else
    if has_client codex; then update_codex_config "$user_home/.codex/config.toml"; fi
    if has_client cursor; then update_json_config "$user_home/.cursor/mcp.json"; fi
    if has_client claude; then
        command -v claude >/dev/null 2>&1 || die "claude is required when --client includes claude"
        claude mcp remove --scope user "$server_name" >/dev/null 2>&1 || true
        claude mcp add --scope user "$server_name" -- "$server_python" "$server_script"
    fi
fi

echo "Installed $server_name for $scope scope."
echo "Runtime: $install_root"
echo "Restart configured clients so they reload MCP servers."
