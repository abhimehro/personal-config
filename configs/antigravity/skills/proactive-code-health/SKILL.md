---
name: proactive-code-health
description: Dead-code removal, targeted test-gap closure, and static-analysis health checks reusing .jules code-health journals and ported Jules review rules.
---

# Proactive Code Health (Maintainability, Dead Code, and Test Coverage Lens)

Deliver **one** verified maintainability improvement per run: safe dead-code
removal, high-value unit test coverage on an untested error/retry/boundary path,
or a concrete correctness lint fix.

## Institutional Memory and Ported Rules

1. Read `<repo>/AGENTS.md` and whichever `.jules/` journals exist in `<repo>`:
   - `.jules/code_health.md`
   - `.jules/testing.md`
   - `.jules/rm_dead_code_dos.md`
   - `.jules/lessons.md`
2. Apply the ported review and severity rules in
   [references/jules-review-rules.md](references/jules-review-rules.md) (`High`
   = blocking correctness/security/system-state risk, `Warning` = meaningful
   debt or fragile edge case, `Info` = low-priority style; skip `Info`-only
   churn).

## Dead-Code Removal Safety Protocol

Before removing any function, helper, script, or export:

1. Search across code, tests, LaunchAgents, Makefiles, GitHub workflows, Fish
   functions, and config templates (`grep` / `ripgrep` across the entire repo).
2. When the `gitnexus` MCP server has indexed the repository, run `gitnexus`
   `impact` (`direction: "upstream"`) on the symbol. If `gitnexus` reports
   `risk: UNKNOWN`, dynamic dispatch, CLI entrypoint exposure, or cross-repo
   usage, **do not delete** the symbol.
3. Never delete files that act as intentional stubs, templates, or manual
   runbooks (such as `launch-agents/*.plist` or disabled
   `.github/workflows/jules*.yml` workflows).

## Test-Addition and Tamper-Evident Harness Protocol

- Adding or extending a unit test (`tests/*`, `*/tests/*`, `Tests/*`,
  `test_*.py`, `test-*.R`) requires passing `--allow-test-edits` to
  `proactive-worktree.sh verify` **only during interactive sessions**, or
  recording the proposed test file in the local report when running unattended.
  Unattended `verify` blocks test-harness and build-harness edits (`Makefile`,
  `pyproject.toml`, `uv.lock`, `requirements*.txt`, `setup.cfg`, `tox.ini`,
  `noxfile.py`, `ruff.toml`, `.ruff.toml`, `.python-version`, `DESCRIPTION`,
  `NAMESPACE`, `.Renviron`, `scripts/*`, `Scripts/*`, `conftest.py`,
  `*/conftest.py`) by default (`exit 2`) so an unattended run cannot pass by
  weakening assertions or linter config.
- Follow `<repo>/docs/TESTING.md` where present (`$MOCK_BIN` PATH injection,
  isolated `$TEST_DIR/home`, BSD/GNU `sed` portability).

## Execution Workflow

1. Check open PR file collisions before editing:
   `$HOME/dev/personal-config/scripts/proactive-worktree.sh check-collisions --repo abhimehro/<repo> --file <relpath>`
2. Prepare an isolated worktree:
   `$HOME/dev/personal-config/scripts/proactive-worktree.sh prepare --repo-path <repo> --lens code-health --mode local`
3. Apply a single minimal production fix and verify without relaxing any harness
   or test gate:
   `$HOME/dev/personal-config/scripts/proactive-worktree.sh verify --worktree <worktree_path> --lens code-health`
4. Commit locally in the worktree using `chore(qa): <concise summary>` and write
   the verification receipt to
   `$HOME/.gemini/antigravity/proactive-reports/YYYY-MM-DD-<repo>.md`.
