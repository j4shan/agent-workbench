#!/bin/bash
# Transport a finite prompt file to Codex; callers select the model and permissions.
set -euo pipefail
fail() { printf 'gpt-exec: %s\n' "$*" >&2; exit 1; }
usage() {
    printf '%s\n' 'Usage: gpt-exec --prompt-file FILE --model ID --reasoning-effort EFFORT --sandbox read-only|workspace-write --project DIR [--json] [--output-last-message FILE]'
}
prompt_file= model= effort= sandbox= project= output= json=0
seen=' '
while [[ $# -gt 0 ]]; do
    option=$1
    case "$option" in
        --prompt-file|--model|--reasoning-effort|--sandbox|--project|--output-last-message)
            [[ $# -ge 2 && -n $2 ]] || fail "$option requires a nonempty value"
            case "$seen" in *" $option "*) fail "duplicate $option" ;; esac
            seen="$seen$option "
            case "$option" in
                --prompt-file) prompt_file=$2 ;;
                --model) model=$2 ;;
                --reasoning-effort) effort=$2 ;;
                --sandbox) sandbox=$2 ;;
                --project) project=$2 ;;
                --output-last-message) output=$2 ;;
            esac
            shift 2 ;;
        --json) [[ $json == 0 ]] || fail 'duplicate --json'; json=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) fail "unknown argument: $option" ;;
    esac
done
[[ -n $prompt_file && -n $model && -n $effort && -n $sandbox && -n $project ]] || fail 'prompt file, model, effort, sandbox, and project are required'
[[ $model =~ ^[A-Za-z0-9][A-Za-z0-9._:/-]*$ ]] || fail 'invalid model ID'
[[ $effort =~ ^[a-z][a-z0-9-]*$ ]] || fail 'invalid reasoning effort'
case "$sandbox" in read-only|workspace-write) ;; *) fail 'sandbox must be read-only or workspace-write' ;; esac
[[ -d $project ]] || fail 'project must be an existing directory'
# Resolve relative paths before handing --cd to the runtime.
project=$(cd "$project" && pwd -P)
[[ -f $prompt_file && -r $prompt_file && -s $prompt_file ]] || fail 'prompt file must be a readable, nonempty regular file'
codex_path=$(command -v codex) || fail 'codex is not on PATH; add the installed executable directory to PATH'
[[ -f $codex_path && -x $codex_path ]] || fail 'codex must resolve to an executable file'
args=(exec --ephemeral --model "$model" --config "model_reasoning_effort=\"$effort\"" --sandbox "$sandbox" --cd "$project")
if [[ $json == 1 ]]; then args+=(--json); fi
if [[ -n $output ]]; then args+=(--output-last-message "$output"); fi
printf 'gpt-exec: model=%s effort=%s sandbox=%s project=%s\n' "$model" "$effort" "$sandbox" "$project" >&2
# exec preserves runtime status and signals; the inherited stdin is never consumed.
exec "$codex_path" "${args[@]}" - < "$prompt_file"
