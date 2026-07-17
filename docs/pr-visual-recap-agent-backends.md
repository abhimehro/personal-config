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
2. Trusted `@agent-native/core` CLI builds `recap-prompt.md`
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

## Operator checklist

1. Confirm secrets: `MISTRAL_API_KEY`, `PLAN_RECAP_TOKEN`
2. Optional repo vars: `VISUAL_RECAP_AGENT=opencode`,
   `VISUAL_RECAP_MODEL=mistral/mistral-medium-latest`
3. Open a non-draft PR (or push to this one) and confirm the sticky recap comment
- Agent (esp. OpenCode) may emit raw newlines inside JSON string literals —
  workflow sanitizes those before publish; still prefer strict JSON from the model
