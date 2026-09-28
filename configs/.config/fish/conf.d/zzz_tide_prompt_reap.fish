# zzz_tide_prompt_reap.fish  — safe to remove
#
# Why this exists:
#   Tide caches a fully rendered ANSI prompt string per shell PID as the
#   universal variable _tide_prompt_<PID>.  When a shell exits, that variable is
#   never removed, so fish_variables grows without bound and every new session
#   pays the cost of parsing the whole file.
#
#   This file sweeps orphaned entries whose PID is no longer a live process, and
#   drops this shell own entry on exit so it never becomes stale.
#
#   Sibling concern: zzz_tide_prompt_guard.fish handles Starship clobbering
#   Tide prompt functions.  This file handles fish_variables bloat.  They are
#   independent; neither replaces the other.
#
# Managed in: ~/dev/personal-config/configs/.config/fish/conf.d/
# Tracked via: .gitignore exception  !configs/.config/fish/conf.d/zzz_tide_prompt_reap.fish
#
# Load order: conf.d is sourced alphabetically, so this runs after
# zzz_tide_prompt_guard.fish.  Order is not significant here, the sweep does not
# depend on prompt functions being installed.

status is-interactive || exit

function __tide_reap_stale_prompts --description "Remove orphaned _tide_prompt_<PID> entries"
    # Skip the sweep entirely when the cache is already small.  A healthy
    # fish_variables holds roughly one entry per live interactive shell (this
    # shell, plus any parent), so a handful of entries is normal and not worth
    # forking ps for on every startup.  Only pay the cost once the file has
    # actually grown.  Kept inside the function on purpose: a file-scope
    # "set -l" does not survive into the function body when this file is
    # sourced from conf.d during startup.
    set -l threshold 3

    set -l names (set -n | string match "_tide_prompt_*")
    test (count $names) -gt $threshold; or return 0

    set -l reaped 0
    for name in $names
        set -l pid (string replace "_tide_prompt_" "" -- $name)

        # Non-numeric suffix: not a PID we can validate, so drop it.
        if not string match -qr '^[0-9]+$' -- $pid
            set -e $name
            set reaped (math $reaped + 1)
            continue
        end

        # A live PID means a live shell still owns this entry.  Anything else
        # is an orphan from a shell that exited without cleaning up.
        if not ps -p $pid -o comm= >/dev/null 2>&1
            set -e $name
            set reaped (math $reaped + 1)
        end
    end

    if test $reaped -gt 0
        set -g __tide_reaped_last $reaped
    end
end

function __tide_reap_own_prompt --on-event fish_exit --description "Drop this shell own Tide prompt cache entry"
    set -l name "_tide_prompt_$fish_pid"
    if set -q $name
        set -e $name
    end
end

__tide_reap_stale_prompts
