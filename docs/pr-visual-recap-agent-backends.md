# PR Visual Recap — alternate agent backends

**Status:** Phase 1 implemented (OpenCode + Mistral)  
**Related:** ABHI-1321 / PR #1670, `.github/workflows/pr-visual-recap.yml`,
`.github/workflows/refactoring-agent.yml`  
**Date:** 2026-07-17 (updated)

## Goal

Run PR Visual Recap without Anthropic Claude or OpenAI Codex, using the same
Mistral Pro / API key stack already proven by CodeScene PR Refactoring.

## Decision (confirmed)

**Phase 1 default = OpenCode + Mistral.** The `MISTRAL_API_KEY` used by
`/cs-agent` is billed through the Pro plan quota, so OpenCode vs Vibe is not a
billing differentiator. Vibe stays optional; Antigravity stays Phase 2 only.

## Hard contract (unchanged)

1. Gate (draft/bot/fork/credential presence, `VISUAL_RECAP_AGENT` allowlist)
2. Trusted `@agent-native/recap-cli` builds `recap-prompt.md` (not
   `@agent-native/core` — core's published bin can `spawn tsx` and fail in CI)
3. **Agent** must leave a non-empty `recap-source.json` in the workspace
4. Deterministic `recap publish` → Plan URL → screenshot → sticky comment

## Configuration

| Name | Values | Notes |
| --- | --- | --- |
| `VISUAL_RECAP_AGENT` | **`opencode`** (default) \| `claude` \| `codex` | Set repo var to override |
| `VISUAL_RECAP_MODEL` | e.g. `mistral/mistral-medium-latest` | OpenCode `provider/model`; defaults to Mistral medium when unset |
| Secrets | `MISTRAL_API_KEY`, `PLAN_RECAP_TOKEN` | Plan token still required for publish |
| Optional | `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | Only if you switch agent back to claude/codex |

Gate (presence-only):

- `opencode` → requires `MISTRAL_API_KEY`
- `claude` → requires `ANTHROPIC_API_KEY`
- `codex` → requires `OPENAI_API_KEY`
- Always → requires `PLAN_RECAP_TOKEN` (same-repo)

## Phase 1 implementation (shipped)

Mirrors CodeScene’s OpenCode auth pattern:

1. Resolve model (`VISUAL_RECAP_MODEL` or `mistral/mistral-medium-latest`)
2. Install pinned `opencode-ai@1.18.3`
3. Write `~/.local/share/opencode/auth.json` (mode 600) from `MISTRAL_API_KEY`
4. **SECURITY:** strip PR-head `opencode.json` / `.opencode`, write least-privilege
   permission config (edit only `recap-source.json`; deny bash/webfetch/websearch)
5. `opencode run -m … --format json --auto` with one retry if
   `recap-source.json` is missing
6. Publisher / screenshot / sticky comment unchanged

Self-modifying guard also skips (on forks / public PRs) when the PR touches
`opencode.json` or `.opencode/`.

## Deferred

| Backend | Status |
| --- | --- |
| Mistral Vibe (`VISUAL_RECAP_AGENT=vibe`) | Optional later — not needed for Pro quota |
| Antigravity (`agy`) | Phase 2 spike only (CI/non-TTY sharp edges) |


## Self-modifying guard

- **Forks:** skip if PR touches `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.mcp.json`,
  `opencode.json`, `.opencode/`, or (when skill source is `repo`) visual skill paths.
- **Same-repo:** skip only for runner-loaded configs (`.claude/`, `.mcp.json`,
  `opencode.json`, `.opencode/`, repo skills) — not `AGENTS.md`/`CLAUDE.md` docs
  edits, which false-skipped owner PRs on public repos.

## Triggers (API cost)

Does **not** run on every push. Default events:

| Event | Runs agent? |
| --- | --- |
| `opened` / `ready_for_review` / `reopened` | Yes (once per lifecycle event) |
| `synchronize` (push) | **No** — removed to protect Mistral/API quota |
| `labeled` with `visual-recap` or `recap` | Yes — explicit refresh |
| `closed` without merge | Skip |
| `closed` + merged | Yes (final sticky update) |

Force a refresh without new commits: add label `visual-recap`, or use Actions →
Re-run jobs on a prior run.

## Operator checklist

1. Confirm secrets: `MISTRAL_API_KEY`, `PLAN_RECAP_TOKEN`
2. Optional repo vars: `VISUAL_RECAP_AGENT=opencode`,
   `VISUAL_RECAP_MODEL=mistral/mistral-medium-latest`,
   `RECAP_CLI_VERSION` (pins `@agent-native/recap-cli`, not core)
3. Open / ready-for-review a non-draft PR and confirm the sticky recap comment
4. On failure at **Collect bounded diff** with `spawn tsx ENOENT`: workflow is
   still on `@agent-native/core` — must use `@agent-native/recap-cli` (Lesson 0eh)
5. On agent failure, download `pr-visual-recap-source-*` artifact
   (`opencode-events.jsonl`, `opencode-stderr.log`)
6. Agent may emit raw newlines inside JSON string literals — workflow prefers
   OpenCode **sidecar files** (`recap-meta.json` + `recap-plan.mdx`, …) and
   assembles strict JSON via `JSON.stringify`; control-char sanitize remains a
   fallback for Claude/Codex single-file output.
