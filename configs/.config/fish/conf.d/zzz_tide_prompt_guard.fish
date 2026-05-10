# zzz_tide_prompt_guard.fish  — DO NOT REMOVE
#
# Why this exists:
#   Kaku's managed fish integration (~/.config/kaku/fish/kaku.fish) runs:
#     starship init fish | source
#   on every session, overwriting Tide's fish_prompt.
#
#   This file is named zzz_… so it loads LAST in conf.d, after kaku.fish and
#   trunk.fish, then tears down Starship's injected functions and re-sources
#   Tide's prompt so it wins every session.
#
# Managed in: ~/dev/personal-config/configs/.config/fish/conf.d/
# Tracked via: .gitignore exception  !configs/.config/fish/conf.d/zzz_tide_prompt_guard.fish

status is-interactive || exit

# ── 1. Remove every function Starship injects ────────────────────────────────
for fn in fish_prompt fish_right_prompt \
           starship_prompt \
           starship_transient_prompt_func \
           starship_transient_rprompt_func \
           __starship_get_time \
           __starship_set_status \
           __starship_update_cmd_duration \
           __starship_preexec_fifo \
           __starship_preexec_all \
           __starship_prompt_status
    functions -e $fn 2>/dev/null
end

# ── 2. Re-source Tide's prompt (autoload alone is not reliable here) ─────────
set -l _tide_fp $__fish_config_dir/functions/fish_prompt.fish
if test -f $_tide_fp
    source $_tide_fp
end

# ── 3. Ensure Dracula syntax colours are applied ─────────────────────────────
if functions -q __ensure_dracula_theme
    __ensure_dracula_theme
end
