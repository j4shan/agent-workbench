#!/bin/bash
# Update one user-owned [model, reasoning-effort] pair. macOS / Bash 3.2.
set -euo pipefail
umask 077

fail() { printf 'subagent-model-upsert: %s\n' "$*" >&2; exit 1; }
usage() {
    printf '%s\n' 'Usage: subagent-model-upsert --role NAME [--model ID] [--reasoning-effort EFFORT] [--lock-timeout SECONDS]'
}
role= model= effort= lock_timeout=10
has_role=0 has_model=0 has_effort=0 has_timeout=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --role|--model|--reasoning-effort|--lock-timeout)
            [[ $# -ge 2 ]] || fail "$1 requires a value"
            case "$1" in
                --role) [[ $has_role == 0 ]] || fail 'duplicate --role'; role=$2; has_role=1 ;;
                --model) [[ $has_model == 0 ]] || fail 'duplicate --model'; model=$2; has_model=1 ;;
                --reasoning-effort) [[ $has_effort == 0 ]] || fail 'duplicate --reasoning-effort'; effort=$2; has_effort=1 ;;
                --lock-timeout) [[ $has_timeout == 0 ]] || fail 'duplicate --lock-timeout'; lock_timeout=$2; has_timeout=1 ;;
            esac
            shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) fail "unknown argument: $1" ;;
    esac
done
[[ $role =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || fail '--role must be lowercase kebab-case'
[[ $has_model == 1 || $has_effort == 1 ]] || fail 'provide --model or --reasoning-effort'
[[ $lock_timeout =~ ^[0-9]{1,2}$ ]] || fail '--lock-timeout must be an integer from 0 to 60'
lock_timeout=$((10#$lock_timeout))
[[ $lock_timeout -le 60 ]] || fail '--lock-timeout must be an integer from 0 to 60'
valid_model() { [[ $1 =~ ^[A-Za-z0-9][A-Za-z0-9._:/-]*$ ]]; }
valid_effort() { [[ $1 =~ ^[a-z][a-z0-9-]*$ ]]; }
if [[ $has_model == 1 ]]; then valid_model "$model" || fail 'invalid model ID'; fi
if [[ $has_effort == 1 ]]; then valid_effort "$effort" || fail 'invalid reasoning effort'; fi
config_dir=${SUBAGENT_MODELS_DIR-"$HOME/Library/Application Support/subagent-models"}
[[ $config_dir == /* ]] || fail 'SUBAGENT_MODELS_DIR must be a nonempty absolute directory'
[[ ! -L $config_dir ]] || fail 'configuration directory must not be a symlink'
mkdir -p "$config_dir"
chmod 700 "$config_dir"
role_file="$config_dir/$role.json"
lock_dir="$role_file.lock"
lock_held=0 temporary=
cleanup() {
    if [[ -n $temporary ]]; then rm -f "$temporary"; fi
    if [[ $lock_held == 1 ]]; then rmdir "$lock_dir" 2>/dev/null || :; fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
deadline=$((SECONDS + lock_timeout))
until mkdir "$lock_dir" 2>/dev/null; do
    [[ -d $lock_dir && ! -L $lock_dir ]] || fail "cannot acquire lock: $lock_dir"
    [[ $SECONDS -lt $deadline ]] || fail "lock timeout: $lock_dir; verify no writer is active before removing a stale lock"
    sleep 0.1
done
lock_held=1
[[ ! -L $role_file ]] || fail 'role file must not be a symlink'
if [[ -e $role_file ]]; then
    [[ -f $role_file ]] || fail 'role path must be a regular file'
    snapshot=$(/usr/bin/plutil -convert json -o - "$role_file" 2>/dev/null) || fail 'existing role file is not valid JSON/plist data'
    array_length=$(/usr/bin/plutil -extract settings raw -expect array -o - - <<< "{\"settings\":$snapshot}" 2>/dev/null) || fail 'role configuration must be an array'
    [[ $array_length == 2 ]] || fail 'role configuration must contain exactly two strings'
    previous_model=$(/usr/bin/plutil -extract 0 raw -expect string -o - - <<< "$snapshot" 2>/dev/null) || fail 'array index 0 must be a model string'
    previous_effort=$(/usr/bin/plutil -extract 1 raw -expect string -o - - <<< "$snapshot" 2>/dev/null) || fail 'array index 1 must be an effort string'
    valid_model "$previous_model" && valid_effort "$previous_effort" || fail 'existing role configuration contains invalid settings'
    if [[ $has_model == 0 ]]; then model=$previous_model; fi
    if [[ $has_effort == 0 ]]; then effort=$previous_effort; fi
else
    [[ $has_model == 1 && $has_effort == 1 ]] || fail 'creating a role requires both --model and --reasoning-effort'
fi
temporary=$(mktemp "$config_dir/.$role.XXXXXX")
# Accepted identifiers contain no quotes, backslashes, control characters, or shell syntax.
printf '["%s","%s"]\n' "$model" "$effort" > "$temporary"
/usr/bin/plutil -convert json -o /dev/null "$temporary"
chmod 600 "$temporary"
mv -f "$temporary" "$role_file"
temporary=
printf 'Updated %s\n' "$role_file"
