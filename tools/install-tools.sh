#!/bin/bash
# Install shared executables explicitly. Never initialize role preferences.
set -euo pipefail
umask 022
fail() { printf 'install-tools: %s\n' "$*" >&2; exit 1; }
bin_dir="$HOME/.local/bin"
force=0 seen_dir=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --bin-dir)
            [[ $# -ge 2 && -n $2 ]] || fail '--bin-dir requires an absolute directory'
            [[ $seen_dir == 0 ]] || fail 'duplicate --bin-dir'
            bin_dir=$2; seen_dir=1; shift 2 ;;
        --force) [[ $force == 0 ]] || fail 'duplicate --force'; force=1; shift ;;
        -h|--help) printf '%s\n' 'Usage: install-tools.sh [--bin-dir ABSOLUTE_DIR] [--force]'; exit 0 ;;
        *) fail "unknown argument: $1" ;;
    esac
done
[[ $bin_dir == /* ]] || fail '--bin-dir must be absolute'
source_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
names=(subagent-model-upsert gpt-exec)
for name in "${names[@]}"; do
    [[ -f "$source_dir/$name.sh" ]] || fail "missing source: $name.sh"
done
mkdir -p "$bin_dir"
lock_dir="$bin_dir/.subagent-tools-install.lock"
mkdir "$lock_dir" 2>/dev/null || fail "installation lock exists or cannot be created: $lock_dir"
staging=
cleanup() {
    if [[ -n $staging ]]; then rm -rf "$staging"; fi
    rmdir "$lock_dir" 2>/dev/null || :
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
# Check every collision before replacing either executable.
for name in "${names[@]}"; do
    target="$bin_dir/$name"
    [[ ! -d $target ]] || fail "destination is a directory: $target"
    if [[ -e $target || -L $target ]]; then
        [[ $force == 1 ]] || fail "destination exists: $target; use --force to replace installed tools"
    fi
done
staging=$(mktemp -d "$bin_dir/.subagent-tools.XXXXXX")
for name in "${names[@]}"; do
    cp "$source_dir/$name.sh" "$staging/$name"
    chmod 755 "$staging/$name"
done
for name in "${names[@]}"; do
    if [[ $force == 1 ]]; then
        mv -f "$staging/$name" "$bin_dir/$name"
    else
        # A hard link fails rather than overwriting a file created after preflight.
        ln "$staging/$name" "$bin_dir/$name"
    fi
    printf 'Installed %s\n' "$bin_dir/$name"
done
