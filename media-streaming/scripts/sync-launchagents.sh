#!/usr/bin/env bash
# ============================================================================
# sync-launchagents.sh — stow-style installer for personal-config LaunchAgents
# ----------------------------------------------------------------------------
# Copies (not symlinks) LaunchAgent plists from the personal-config repo into
# ~/Library/LaunchAgents, then unloads + reloads each one via launchctl.
#
# Why copy instead of symlink?
#   - Mole's orphan/stale heuristics (clean_orphaned_app_data, hints.sh) flag
#     broken symlinks as "stale login items" and may delete the symlink.
#   - launchctl bootstrap occasionally errors out (EIO 5) when the plist is a
#     dangling or recently re-pointed symlink.
#   - Real files survive `mo purge`, Time Machine restores, and macOS upgrades.
#
# Design:
#   - Source of truth: ~/dev/personal-config/media-streaming/launchd/*.plist
#   - Each plist is checksummed; only changed/new ones get redeployed.
#   - Existing entries are bootout'd cleanly before the new copy is bootstrap'd.
#   - Stale plists in ~/Library/LaunchAgents that match com.speedybee.* but no
#     longer exist in the repo are reported (and removed with --prune).
#
# Usage:
#   sync-launchagents.sh                 # sync all, idempotent
#   sync-launchagents.sh --dry-run       # show what would change, no writes
#   sync-launchagents.sh --prune         # also remove orphan plists in dest
#   sync-launchagents.sh --force         # redeploy even if checksums match
#   sync-launchagents.sh --verbose       # extra logging
#   sync-launchagents.sh --status        # just print current state
#   sync-launchagents.sh com.speedybee.media.server  # sync a single label
# ============================================================================

set -euo pipefail

# ── Config ─────────────────────────────────────────────────────────────────
readonly REPO_ROOT="${REPO_ROOT:-$HOME/dev/personal-config}"
readonly SRC_DIRS=(
    "$REPO_ROOT/media-streaming/launchd"
    "$REPO_ROOT/launch-agents"
)
readonly DEST_DIR="$HOME/Library/LaunchAgents"
readonly LOG_DIR="$HOME/Library/Logs"
readonly STATE_DIR="$HOME/.local/state/sync-launchagents"
readonly STATE_FILE="$STATE_DIR/manifest.tsv"
readonly LABEL_PREFIX_FILTER="com.speedybee."  # for --prune scoping

# ── Colors ─────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
    readonly C_GREEN=$'\033[32m'
    readonly C_YELLOW=$'\033[33m'
    readonly C_RED=$'\033[31m'
    readonly C_GRAY=$'\033[90m'
    readonly C_BOLD=$'\033[1m'
    readonly C_RESET=$'\033[0m'
else
    readonly C_GREEN="" C_YELLOW="" C_RED="" C_GRAY="" C_BOLD="" C_RESET=""
fi

# ── Flags ──────────────────────────────────────────────────────────────────
DRY_RUN=false
PRUNE=false
FORCE=false
VERBOSE=false
STATUS_ONLY=false
ONLY_LABEL=""

usage() {
    sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
    exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run|-n) DRY_RUN=true ;;
        --prune)      PRUNE=true ;;
        --force|-f)   FORCE=true ;;
        --verbose|-v) VERBOSE=true ;;
        --status|-s)  STATUS_ONLY=true ;;
        -h|--help)    usage 0 ;;
        com.*)        ONLY_LABEL="$1" ;;
        *) printf '%sUnknown argument:%s %s\n' "$C_RED" "$C_RESET" "$1" >&2; usage 2 ;;
    esac
    shift
done

# ── Logging helpers ────────────────────────────────────────────────────────
log()   { printf '%s%s%s %s\n' "$C_GRAY" "[$(date '+%H:%M:%S')]" "$C_RESET" "$*"; }
info()  { log "${C_BOLD}$*${C_RESET}"; }
ok()    { log "${C_GREEN}✓${C_RESET} $*"; }
warn()  { log "${C_YELLOW}⚠${C_RESET} $*"; }
err()   { log "${C_RED}✗${C_RESET} $*" >&2; }
dbg()   { [[ "$VERBOSE" == "true" ]] && log "${C_GRAY}· $*${C_RESET}" || true; }
dry()   { [[ "$DRY_RUN" == "true" ]] && printf '%s[DRY-RUN]%s ' "$C_YELLOW" "$C_RESET" || true; }

# ── Sanity ─────────────────────────────────────────────────────────────────
[[ "$(uname -s)" == "Darwin" ]] || { err "macOS only."; exit 1; }
command -v launchctl >/dev/null || { err "launchctl missing."; exit 1; }
command -v plutil    >/dev/null || { err "plutil missing.";    exit 1; }
command -v shasum    >/dev/null || { err "shasum missing.";    exit 1; }

mkdir -p "$DEST_DIR" "$LOG_DIR" "$STATE_DIR"

UID_NUM="$(id -u)"
DOMAIN="gui/$UID_NUM"

# ── Discover source plists ─────────────────────────────────────────────────
declare -a SRC_PLISTS=()
for d in "${SRC_DIRS[@]}"; do
    [[ -d "$d" ]] || { dbg "skipping missing source dir: $d"; continue; }
    while IFS= read -r -d '' f; do
        SRC_PLISTS+=("$f")
    done < <(find "$d" -maxdepth 1 -type f -name '*.plist' -print0 2>/dev/null)
done

if [[ ${#SRC_PLISTS[@]} -eq 0 ]]; then
    err "No source plists found in: ${SRC_DIRS[*]}"
    exit 1
fi

# Optional single-label filter
if [[ -n "$ONLY_LABEL" ]]; then
    declare -a FILTERED=()
    for p in "${SRC_PLISTS[@]}"; do
        [[ "$(basename "$p")" == "${ONLY_LABEL}.plist" ]] && FILTERED+=("$p")
    done
    if [[ ${#FILTERED[@]} -eq 0 ]]; then
        err "Label not found in repo: $ONLY_LABEL"
        exit 1
    fi
    SRC_PLISTS=("${FILTERED[@]}")
fi

# ── Helpers ────────────────────────────────────────────────────────────────
plist_label() {
    local p="$1" label
    label="$(plutil -extract Label raw "$p" 2>/dev/null || true)"
    [[ -z "$label" ]] && label="$(basename "$p" .plist)"
    printf '%s' "$label"
}

sum_file() { shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'; }

is_loaded() { launchctl print "$DOMAIN/$1" >/dev/null 2>&1; }

current_pid() {
    launchctl list 2>/dev/null | awk -v l="$1" '$3==l {print $1}'
}

last_exit() {
    launchctl list 2>/dev/null | awk -v l="$1" '$3==l {print $2}'
}

unload_label() {
    local label="$1"
    if is_loaded "$label"; then
        dbg "bootout $DOMAIN/$label"
        launchctl bootout "$DOMAIN/$label" 2>/dev/null || true
        # Give launchd a moment to release the label
        local i=0
        while is_loaded "$label" && [[ $i -lt 10 ]]; do sleep 0.2; i=$((i+1)); done
    fi
    launchctl remove "$label" 2>/dev/null || true
}

bootstrap_label() {
    local label="$1" plist="$2"
    if launchctl bootstrap "$DOMAIN" "$plist" 2>/dev/null; then
        launchctl enable "$DOMAIN/$label" 2>/dev/null || true
        return 0
    fi

    # If launchd reports the label as already loaded after bootout, do not use
    # legacy `load -w`; that can leave the old job definition active. Remove it,
    # wait briefly, then retry bootstrap from the copied plist.
    warn "bootstrap failed for $label, removing stale label and retrying"
    launchctl bootout "$DOMAIN/$label" 2>/dev/null || true
    launchctl remove "$label" 2>/dev/null || true
    sleep 1
    if launchctl bootstrap "$DOMAIN" "$plist" 2>/dev/null; then
        launchctl enable "$DOMAIN/$label" 2>/dev/null || true
        return 0
    fi

    warn "bootstrap retry failed for $label; retrying with legacy load -w"
    launchctl load -w "$plist" 2>/dev/null
}

kill_lingering_for_label() {
    # Kill any process whose ProgramArguments include the plist's script path,
    # which prevents bootstrap EIO 5 when launchd thinks the job is still alive.
    # Pipes are tolerated to non-zero (grep finding nothing is fine).
    local label="$1" plist="$2"
    local prog_args=""
    prog_args="$( { plutil -convert xml1 -o - "$plist" 2>/dev/null \
        | awk '/<key>ProgramArguments<\/key>/,/<\/array>/' \
        | sed -n 's@.*<string>\(.*\)</string>.*@\1@p' \
        | grep -E '\.(sh|py)( |$)' ; true; } | head -3)"
    [[ -z "$prog_args" ]] && return 0
    while IFS= read -r script; do
        [[ -n "$script" ]] || continue
        if pgrep -fl -- "$script" >/dev/null 2>&1; then
            dbg "killing lingering processes for $script"
            pkill -f -- "$script" 2>/dev/null || true
        fi
    done <<< "$prog_args"
    return 0
}

# ── Status mode ────────────────────────────────────────────────────────────
print_status() {
    printf '%s%-42s %-10s %-10s %-8s %s%s\n' \
        "$C_BOLD" "LABEL" "PID" "LAST_EXIT" "LOADED" "SOURCE" "$C_RESET"
    for src in "${SRC_PLISTS[@]}"; do
        local label pid lex loaded
        label="$(plist_label "$src")"
        pid="$(current_pid "$label")"; pid="${pid:--}"
        lex="$(last_exit "$label")";    lex="${lex:--}"
        if is_loaded "$label"; then loaded="${C_GREEN}yes${C_RESET}"; else loaded="${C_RED}no${C_RESET} "; fi
        printf '%-42s %-10s %-10s %-17s %s\n' \
            "$label" "$pid" "$lex" "$loaded" "${src/#$HOME/~}"
    done
}

if [[ "$STATUS_ONLY" == "true" ]]; then
    info "LaunchAgent status"
    print_status
    exit 0
fi

# ── Main sync loop ─────────────────────────────────────────────────────────
info "Syncing ${#SRC_PLISTS[@]} LaunchAgent(s) from personal-config → $DEST_DIR"
[[ "$DRY_RUN" == "true" ]] && warn "Dry-run mode: no writes, no launchctl mutations."

declare -i installed=0 updated=0 unchanged=0 failed=0
tmp_manifest="$(mktemp)"
trap 'rm -f "$tmp_manifest"' EXIT

for src in "${SRC_PLISTS[@]}"; do
    label="$(plist_label "$src")"
    fname="$(basename "$src")"
    dst="$DEST_DIR/$fname"

    # Lint first — never deploy a broken plist
    if ! plutil -lint "$src" >/dev/null 2>&1; then
        err "lint failed, skipping: $label ($src)"
        failed+=1
        continue
    fi

    src_sum="$(sum_file "$src")"
    dst_sum=""
    dst_kind="absent"

    if [[ -L "$dst" ]]; then
        dst_kind="symlink"
        if [[ -e "$dst" ]]; then
            dst_sum="$(sum_file "$dst")"
        fi
    elif [[ -f "$dst" ]]; then
        dst_kind="file"
        dst_sum="$(sum_file "$dst")"
    fi

    needs_install=false
    if [[ "$FORCE" == "true" ]]; then
        needs_install=true
        action="force"
    elif [[ "$dst_kind" == "absent" ]]; then
        needs_install=true; action="install"
    elif [[ "$dst_kind" == "symlink" ]]; then
        needs_install=true; action="convert-symlink-to-file"
    elif [[ "$src_sum" != "$dst_sum" ]]; then
        needs_install=true; action="update"
    else
        action="unchanged"
    fi

    printf '%s%-32s%s [%s] %s\n' "$C_BOLD" "$label" "$C_RESET" "$dst_kind" "$action"
    printf '  %s%s%s → %s%s%s\n' \
        "$C_GRAY" "${src/#$HOME/~}" "$C_RESET" \
        "$C_GRAY" "${dst/#$HOME/~}" "$C_RESET"

    if ! "$needs_install"; then
        unchanged+=1
        printf '%s\t%s\t%s\tunchanged\n' "$label" "$src_sum" "$dst" >> "$tmp_manifest"
        continue
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        dbg "would unload, replace, and bootstrap $label"
        [[ "$action" == "install" ]] && installed+=1 || updated+=1
        continue
    fi

    # 1. Unload current instance
    unload_label "$label"
    kill_lingering_for_label "$label" "$src"

    # 2. Replace destination with a real file copy (overwriting symlink if any)
    rm -f "$dst"
    if ! cp -f "$src" "$dst"; then
        err "copy failed: $src → $dst"
        failed+=1
        continue
    fi
    chmod 644 "$dst"

    # 3. Bootstrap fresh
    if bootstrap_label "$label" "$dst"; then
        ok "deployed $label (action=$action)"
        [[ "$action" == "install" ]] && installed+=1 || updated+=1
        printf '%s\t%s\t%s\t%s\n' "$label" "$src_sum" "$dst" "$action" >> "$tmp_manifest"
    else
        err "bootstrap failed: $label — file copied but service not loaded"
        failed+=1
    fi
done

# ── Prune orphan plists in destination ─────────────────────────────────────
if [[ "$PRUNE" == "true" ]]; then
    info "Pruning orphan ${LABEL_PREFIX_FILTER}*.plist entries in $DEST_DIR"
    while IFS= read -r -d '' dst; do
        fname="$(basename "$dst")"
        # Is there a source plist with the same name?
        found=false
        for d in "${SRC_DIRS[@]}"; do
            [[ -f "$d/$fname" ]] && { found=true; break; }
        done
        if "$found"; then
            dbg "keep (has source): $fname"
            continue
        fi

        label="${fname%.plist}"
        # Only prune if the file is broken (symlink to nowhere) or matches our prefix
        is_broken_symlink=false
        [[ -L "$dst" && ! -e "$dst" ]] && is_broken_symlink=true

        if "$is_broken_symlink" || [[ "$label" == ${LABEL_PREFIX_FILTER}* ]]; then
            warn "orphan: $fname (no source in repo)"
            if [[ "$DRY_RUN" == "true" ]]; then
                dry; echo "would unload + remove $fname"
                continue
            fi
            unload_label "$label"
            rm -f "$dst"
            ok "pruned $fname"
        fi
    done < <(find "$DEST_DIR" -maxdepth 1 \( -type f -o -type l \) -name "${LABEL_PREFIX_FILTER}*.plist" -print0 2>/dev/null)
fi

# ── Persist manifest (for change tracking / future diffing) ────────────────
if [[ "$DRY_RUN" != "true" ]]; then
    mv -f "$tmp_manifest" "$STATE_FILE"
    dbg "manifest written: $STATE_FILE"
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo
info "Summary"
printf '  installed: %s%d%s\n' "$C_GREEN"  "$installed" "$C_RESET"
printf '  updated:   %s%d%s\n' "$C_GREEN"  "$updated"   "$C_RESET"
printf '  unchanged: %s%d%s\n' "$C_GRAY"   "$unchanged" "$C_RESET"
printf '  failed:    %s%d%s\n' "$C_RED"    "$failed"    "$C_RESET"
echo
info "Post-sync status"
print_status

exit $(( failed > 0 ? 1 : 0 ))
