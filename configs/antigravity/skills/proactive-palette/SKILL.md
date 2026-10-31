---
name: proactive-palette
description: CLI and application UX, TTY safety, NO_COLOR compliance, and actionable error messages reusing .jules/palette.md memory. Disabled on scientific research repositories.
---

# Proactive Palette (CLI/UI Ergonomics and Accessibility Lens)

Deliver **one** small, high-clarity usability or accessibility improvement for
interactive CLIs, developer scripts, or desktop/web UIs.

## Scope Exclusion (Research Repositories)

Palette is **disabled** on scientific analysis repositories
(`Hydrograph_Versus_Seatek_Sensors_Project`, `Seatek_Analysis`, and
`series_correction_project_updated`). `proactive-worktree.sh` enforces this rule
(`exit 3`) so batch scientific scripts and reproducible figure pipelines do not
accumulate cosmetic churn.

Eligible repositories: `ctrld-sync`, `email-security-pipeline`,
`personal-config`, and (after `1A` graduation) `repoprompt-ce`. Note that
`scripts/*` and `Scripts/*` are tamper-evident harness directories in
`proactive-worktree.sh verify` unless `--allow-harness-changes` is explicitly
authorized; in `personal-config`, prefer non-harness operational surfaces such
as `maintenance/bin/*`, `media-streaming/scripts/*`,
`controld-system/scripts/*`, and `raycast-scripts/*`.

## Focus Areas

1. **TTY and Non-Interactive Hygiene:**
   - Guard ANSI colors, spinners, and cursor-movement escape codes behind
     `[[ -t 1 ]]` / `sys.stdout.isatty()` and honor `NO_COLOR` and `TERM=dumb`.
   - Ensure scripts invoked from `launchd`, cron, or CI never block on
     interactive `read` prompts without a non-TTY fallback or clear exit
     message.
2. **Actionable Error Diagnostics:**
   - Replace cryptic non-zero exits with concise `stderr` messages stating what
     failed, why, and the exact recovery command (without echoing sensitive
     values).
   - Provide `--help` / `-h` usage output that exits `0` cleanly and documents
     required flags and safe dry-run options.
3. **Safe Defaults and Confirmation Prompts:**
   - Ensure destructive or state-mutating operations support `--dry-run` or
     print clear before/after state summaries.

## Execution Workflow

1. Read `<repo>/AGENTS.md` and `<repo>/.jules/palette.md` to avoid repeating
   completed polish passes or violating house style.
2. Verify no open PR touches the candidate file:
   `$HOME/dev/personal-config/scripts/proactive-worktree.sh check-collisions --repo abhimehro/<repo> --file <relpath>`
3. Create an isolated worktree:
   `$HOME/dev/personal-config/scripts/proactive-worktree.sh prepare --repo-path <repo> --lens palette --mode local`
4. Implement the change with zero impact on machine-parsed stdout contracts, and
   verify with:
   `$HOME/dev/personal-config/scripts/proactive-worktree.sh verify --worktree <worktree_path> --lens palette`
5. Commit locally in the worktree using title prefix
   `🎨palette: <concise summary>` and summarize before/after UX output in
   `$HOME/.gemini/antigravity/proactive-reports/YYYY-MM-DD-<repo>.md`.
