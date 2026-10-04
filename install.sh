#!/usr/bin/env bash
#
# Install this repository's skills and instructions.
#
# Each client is given the content in the shape it actually loads. Default
# --scope project writes into a target project. --scope user writes into the
# current user's client directories.

set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<'EOF'
Usage:
  install.sh [--scope project] <project-dir> [skill,skill,...]
  install.sh --scope user [skill,skill,...]

Copy skills and instructions at the paths each client reads.

  --scope project|user   install destination (default: project)
  <project-dir>          target project root (required for --scope project)
  [skill,skill,...]      install only these skills (comma-separated names).
                         Omit to install every included skill.
  -h, --help             show this message

Inclusion is read from install.yaml next to this script. true copies the
item; false skips it. A name missing from the file is treated as true.

Project destinations (--scope project):
  Skills          <project>/.agents/skills/<name>/
  Cursor rules    <project>/.cursor/rules/<name>.mdc
  Claude rules    <project>/.claude/rules/<name>.md

User destinations (--scope user):
  Skills          ~/.cursor/skills/<name>/ and ~/.claude/skills/<name>/
  Cursor rules    ~/.cursor/rules/<name>.mdc
  Claude rules    ~/.claude/rules/<name>.md
EOF
}

die() {
    echo "error: $*" >&2
    echo >&2
    usage >&2
    exit 1
}

# ------------------------------------------------------------------- flags

scope=project
positionals=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        --scope)
            [[ $# -ge 2 ]] || die "--scope requires project or user"
            scope="$2"
            shift 2
            ;;
        --scope=*)
            scope="${1#--scope=}"
            shift
            ;;
        --)
            shift
            positionals+=("$@")
            break
            ;;
        -*)
            die "unknown argument '$1'"
            ;;
        *)
            positionals+=("$1")
            shift
            ;;
    esac
done

case "$scope" in
    project|user) ;;
    *) die "--scope must be project or user (got '$scope')" ;;
esac

skill_filter=""
PROJECT=""

if [[ "$scope" == project ]]; then
    [[ ${#positionals[@]} -ge 1 ]] || die "project directory required for --scope project"
    [[ ${#positionals[@]} -le 2 ]] || die "too many arguments (got ${#positionals[@]})"
    PROJECT="${positionals[0]}"
    skill_filter="${positionals[1]-}"
    [[ ! "$PROJECT" == -* ]] || die "unknown argument '$PROJECT'"
    [[ -d "$PROJECT" ]] || { echo "error: not a directory: $PROJECT" >&2; exit 1; }
    PROJECT="$(cd "$PROJECT" && pwd)"
    if [[ "$PROJECT" == "$SRC" ]]; then
        echo "error: refuse to install into this repository ($SRC)" >&2
        exit 1
    fi
else
    [[ ${#positionals[@]} -le 1 ]] || die "too many arguments for --scope user (got ${#positionals[@]})"
    if [[ ${#positionals[@]} -eq 1 ]]; then
        skill_filter="${positionals[0]}"
        if [[ -d "$skill_filter" ]]; then
            die "--scope user takes no project directory ('$skill_filter' is a directory)"
        fi
    fi
fi

# ----------------------------------------------------------- inclusion config

CONFIG="$SRC/install.yaml"

if [[ ! -f "$CONFIG" ]]; then
    echo "error: missing install config: $CONFIG" >&2
    exit 1
fi

# Prints true or false for kind (skills|instructions) and item name.
# A name missing from install.yaml is true. Keys may carry .md.
inclusion_default() {
    local kind="$1" name="$2"
    local section="" line key val
    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%$'\r'}"
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ "$line" =~ ^[[:space:]]*$ ]] && continue
        if [[ "$line" =~ ^([A-Za-z0-9_-]+):[[:space:]]*$ ]]; then
            section="${BASH_REMATCH[1]}"
            continue
        fi
        if [[ "$line" =~ ^[[:space:]]+([A-Za-z0-9._-]+):[[:space:]]*(true|false|yes|no)[[:space:]]*$ ]]; then
            key="${BASH_REMATCH[1]}"
            key="${key%.md}"
            val="${BASH_REMATCH[2]}"
            if [[ "$section" == "$kind" && "$key" == "$name" ]]; then
                case "$val" in
                    true|yes) printf '%s\n' true ;;
                    false|no) printf '%s\n' false ;;
                esac
                return 0
            fi
            continue
        fi
        echo "error: invalid line in install.yaml: $line" >&2
        return 1
    done < "$CONFIG"
    printf '%s\n' true
}

# ------------------------------------------------------------------ what to copy

# A skill is any directory carrying a SKILL.md. Selecting on the marker file
# rather than on "every directory" is what keeps skills/README.md out without
# naming it.
skills=()
for dir in "$SRC"/skills/*/; do
    [[ -f "${dir}SKILL.md" ]] && skills+=("${dir%/}")
done

# README.md documents the directory for a human reading the repository; it is not
# an instruction and must not be installed as one.
instructions=()
for file in "$SRC"/instructions/*.md; do
    [[ -f "$file" ]] || continue
    [[ "$(basename "$file")" == "README.md" ]] && continue
    instructions+=("$file")
done

if [[ -n "$skill_filter" ]]; then
    compact="${skill_filter//[[:space:]]/}"
    if [[ "$compact" == ,* || "$compact" == *, || "$compact" == *,,* ]]; then
        echo "error: empty skill name in list: $skill_filter" >&2
        exit 1
    fi

    requested=()
    IFS=',' read -ra raw <<< "$skill_filter"
    for token in "${raw[@]}"; do
        name="${token#"${token%%[![:space:]]*}"}"
        name="${name%"${name##*[![:space:]]}"}"
        if [[ -z "$name" ]]; then
            echo "error: empty skill name in list: $skill_filter" >&2
            exit 1
        fi
        requested+=("$name")
    done

    selected=()
    seen_csv=
    for name in "${requested[@]}"; do
        case ",$seen_csv," in
            *",$name,"*) continue ;;
        esac
        seen_csv="${seen_csv:+$seen_csv,}$name"

        found=
        for skill in "${skills[@]}"; do
            if [[ "$(basename "$skill")" == "$name" ]]; then
                selected+=("$skill")
                found=1
                break
            fi
        done
        if [[ -z "$found" ]]; then
            echo "error: unknown skill '$name'" >&2
            echo "available:" >&2
            for skill in "${skills[@]}"; do
                echo "  $(basename "$skill")" >&2
            done
            exit 1
        fi
    done
    skills=("${selected[@]}")
fi

included_skills=()
if [[ ${#skills[@]} -gt 0 ]]; then
    for skill in "${skills[@]}"; do
        name="$(basename "$skill")"
        inc="$(inclusion_default skills "$name")" || exit 1
        if [[ "$inc" == true ]]; then
            included_skills+=("$skill")
        elif [[ -n "$skill_filter" ]]; then
            echo "error: skill '$name' is excluded by install.yaml" >&2
            exit 1
        fi
    done
fi
if [[ ${#included_skills[@]} -gt 0 ]]; then
    skills=("${included_skills[@]}")
else
    skills=()
fi

included_instructions=()
if [[ ${#instructions[@]} -gt 0 ]]; then
    for file in "${instructions[@]}"; do
        name="$(basename "$file" .md)"
        inc="$(inclusion_default instructions "$name")" || exit 1
        if [[ "$inc" == true ]]; then
            included_instructions+=("$file")
        fi
    done
fi
if [[ ${#included_instructions[@]} -gt 0 ]]; then
    instructions=("${included_instructions[@]}")
else
    instructions=()
fi

if [[ ${#skills[@]} -eq 0 && ${#instructions[@]} -eq 0 ]]; then
    echo "error: nothing to install — no skills or instructions found under $SRC" >&2
    exit 1
fi

# ---------------------------------------------------------------- destinations

if [[ "$scope" == project ]]; then
    cursor_skills_roots=("$PROJECT/.agents/skills")
    claude_skills_roots=()
    cursor_rules_root="$PROJECT/.cursor/rules"
    claude_rules_root="$PROJECT/.claude/rules"
else
    cursor_skills_roots=("$HOME/.cursor/skills")
    claude_skills_roots=("$HOME/.claude/skills")
    cursor_rules_root="$HOME/.cursor/rules"
    claude_rules_root="$HOME/.claude/rules"
fi

# ------------------------------------------------------------ collision handling

# Every destination that already exists is gathered before anything is written,
# so the user answers one question about the whole run rather than one per item.
collisions=()
if [[ ${#skills[@]} -gt 0 ]]; then
    for skill in "${skills[@]}"; do
        name="$(basename "$skill")"
        for root in "${cursor_skills_roots[@]}"; do
            [[ -e "$root/$name" ]] && collisions+=("$root/$name")
        done
        if [[ ${#claude_skills_roots[@]} -gt 0 ]]; then
            for root in "${claude_skills_roots[@]}"; do
                [[ -e "$root/$name" ]] && collisions+=("$root/$name")
            done
        fi
    done
fi
if [[ ${#instructions[@]} -gt 0 ]]; then
    for instruction in "${instructions[@]}"; do
        name="$(basename "$instruction" .md)"
        [[ -e "$cursor_rules_root/${name}.mdc" ]] && collisions+=("$cursor_rules_root/${name}.mdc")
        [[ -e "$claude_rules_root/${name}.md" ]] && collisions+=("$claude_rules_root/${name}.md")
    done
fi

overwrite=yes
if [[ ${#collisions[@]} -gt 0 ]]; then
    echo "Already present:"
    printf '  %s\n' "${collisions[@]}"
    echo
    read -r -p "${#collisions[@]} existing item(s) will be overwritten. Overwrite? [Y/n] " answer
    case "${answer:-Y}" in
        [Yy]*)  overwrite=yes ;;
        *)      overwrite=no; echo "Skipping all existing items." ;;
    esac
    echo
fi

# Returns 0 when the destination should be written.
should_write() {
    [[ ! -e "$1" || "$overwrite" == yes ]]
}

# ------------------------------------------------------------------- conversion

# Cursor loads a rule only if it carries frontmatter telling it when to apply.
# The description is the document's H1, so the agent has something to match on.
write_cursor_rule() {
    local source="$1" dest="$2" description
    description="$(sed -n 's/^# //p' "$source" | head -1)"
    [[ -z "$description" ]] && description="$(basename "$source" .md)"

    {
        printf -- '---\n'
        printf 'description: %s\n' "$description"
        printf 'alwaysApply: true\n'
        printf -- '---\n\n'
        cat "$source"
    } > "$dest"
}

copy_skill() {
    local skill="$1" dest="$2" name="$3" label="$4"
    if should_write "$dest"; then
        # Replaced whole, so a file deleted upstream cannot survive here.
        rm -rf "$dest"
        mkdir -p "$(dirname "$dest")"
        cp -R "$skill" "$dest"
        echo "   $label $name -> $dest"
        installed=$((installed + 1))
    else
        echo "   $label $name -- skipped (exists)"
        skipped=$((skipped + 1))
    fi
}

# ---------------------------------------------------------------------- install

installed=0
skipped=0

mkdir -p "$cursor_rules_root" "$claude_rules_root"
for root in "${cursor_skills_roots[@]}"; do
    mkdir -p "$root"
done
if [[ ${#claude_skills_roots[@]} -gt 0 ]]; then
    for root in "${claude_skills_roots[@]}"; do
        mkdir -p "$root"
    done
fi

if [[ "$scope" == project ]]; then
    echo "== $PROJECT"
else
    echo "== user ($HOME)"
fi

if [[ ${#skills[@]} -gt 0 ]]; then
    for skill in "${skills[@]}"; do
        name="$(basename "$skill")"
        copy_skill "$skill" "${cursor_skills_roots[0]}/$name" "$name" "skill            "
        if [[ ${#claude_skills_roots[@]} -gt 0 ]]; then
            copy_skill "$skill" "${claude_skills_roots[0]}/$name" "$name" "skill/claude     "
        fi
    done
fi

if [[ ${#instructions[@]} -gt 0 ]]; then
    for instruction in "${instructions[@]}"; do
        name="$(basename "$instruction" .md)"

        dest="$cursor_rules_root/${name}.mdc"
        if should_write "$dest"; then
            mkdir -p "$cursor_rules_root"
            write_cursor_rule "$instruction" "$dest"
            echo "   instruction/cursor $name -> $dest"
            installed=$((installed + 1))
        else
            echo "   instruction/cursor $name -- skipped (exists)"
            skipped=$((skipped + 1))
        fi

        dest="$claude_rules_root/${name}.md"
        if should_write "$dest"; then
            mkdir -p "$claude_rules_root"
            cp "$instruction" "$dest"
            echo "   instruction/claude $name -> $dest"
            installed=$((installed + 1))
        else
            echo "   instruction/claude $name -- skipped (exists)"
            skipped=$((skipped + 1))
        fi
    done
fi

echo

# ----------------------------------------------------------------------- report

echo "Installed $installed item(s), skipped $skipped."

echo
echo "Restart the client — skills and rules are read at session start."

# -------------------------------------------------------- user-scope leftovers

if [[ "$scope" != project ]]; then
    exit 0
fi

leftover_dirs=()
leftover_files=()
if [[ ${#skills[@]} -gt 0 ]]; then
    for skill in "${skills[@]}"; do
        name="$(basename "$skill")"
        [[ -e "$HOME/.cursor/skills/$name" ]] && leftover_dirs+=("$HOME/.cursor/skills/$name")
        [[ -e "$HOME/.claude/skills/$name" ]] && leftover_dirs+=("$HOME/.claude/skills/$name")
    done
fi
if [[ ${#instructions[@]} -gt 0 ]]; then
    for instruction in "${instructions[@]}"; do
        name="$(basename "$instruction" .md)"
        [[ -e "$HOME/.cursor/rules/${name}.mdc" ]] && leftover_files+=("$HOME/.cursor/rules/${name}.mdc")
        [[ -e "$HOME/.claude/rules/${name}.md" ]] && leftover_files+=("$HOME/.claude/rules/${name}.md")
    done
fi
echo
if [[ ${#leftover_dirs[@]} -eq 0 && ${#leftover_files[@]} -eq 0 ]]; then
    echo "No user-scope leftovers from an earlier install."
else
    echo "User-scope leftovers from an earlier install (safe to remove if you no longer"
    echo "want these applied to every project):"
    echo
    if [[ ${#leftover_dirs[@]} -gt 0 ]]; then
        for dest in "${leftover_dirs[@]}"; do
            echo "  rm -rf $dest"
        done
    fi
    if [[ ${#leftover_files[@]} -gt 0 ]]; then
        for dest in "${leftover_files[@]}"; do
            echo "  rm -f $dest"
        done
    fi
fi
