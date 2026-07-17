# PR Visual Recap — alternate agent backends (draft)

**Status:** design draft (not implemented)  
**Related:** ABHI-1321 / PR #1670, `.github/workflows/pr-visual-recap.yml`,
`.github/workflows/refactoring-agent.yml`  
**Date:** 2026-07-17

## Goal

Run PR Visual Recap without Anthropic Claude or OpenAI Codex, using tooling you
already pay for (Mistral Pro / Vibe, and optionally Google Antigravity).

## Hard contract (must not change)

The agent step is a black box. Everything around it stays:

1. Gate (draft/bot/fork/secret presence, `VISUAL_RECAP_AGENT` allowlist)
2. Trusted `@agent-native/core` CLI builds `recap-prompt.md`
3. **Agent** must leave a non-empty `recap-source.json` in the workspace
4. Deterministic `recap publish` → Plan URL → screenshot → sticky comment

So a new backend only needs to: read `recap-prompt.md`, use tools to inspect the
diff, **write `recap-source.json`**, exit 0. Publisher validates MDX.

## Option comparison

| Backend | CI readiness | Reuses repo config | Pro-plan quota fit | Seamlessness |
| --- | --- | --- | --- | --- |
| **Mistral Vibe CLI** | Strong — documented `--prompt` / programmatic / `auto-approve` | Shares `MISTRAL_API_KEY` pattern; Pro Vibe is the natural client | **Best** if Pro includes Vibe Code | High for *billing*; medium for *workflow code* (new step) |
| **OpenCode + Mistral** | Strong — already used in `refactoring-agent.yml` | **Best** reuse: `ENABLE_MISTRAL`, `MISTRAL_API_KEY`, `auth.json`, model `mistral/…` | Depends whether that key is API payg vs Pro | **Best** for *code reuse* |
| **Antigravity (`agy`)** | Weak–medium — headless exists but non-TTY stdout bugs (#76), auth/PTY workarounds | New secrets (`ANTIGRAVITY_*`); Google billing | Unclear vs your “Gemini pay-as-you-use” concern | Lowest for CI today |
| Claude / Codex (current) | Strong | Needs paid Anthropic/OpenAI | N/A for you | Already wired |

### Recommendation

**Phase 1 (ship first): OpenCode + Mistral**, mirroring CodeScene.

Why:

- You already run this stack successfully for `/cs-agent`
- Same secrets/vars (`MISTRAL_API_KEY`, `ENABLE_MISTRAL`, optional model var)
- Same auth.json construction (copy the “Configure OpenCode auth” step)
- Stable headless behavior vs Antigravity’s current CI sharp edges

**Also wire Phase 1b: Mistral Vibe** behind `VISUAL_RECAP_AGENT=vibe` if Pro
quota is billed through Vibe rather than the raw API key OpenCode uses.
Confirm which meter your existing `MISTRAL_API_KEY` hits before choosing a
default.

**Phase 2 (optional): Antigravity** only after a spike proves:

- Non-interactive auth without browser OAuth on `ubuntu-latest`
- Reliable capture of agent output (PTY/`script` workaround or fixed `#76`)
- Agent can Write `recap-source.json` with auto-approve policy
- Cost stays acceptable under your Google/Antigravity plan

Do **not** make Antigravity the default until that spike is green.

## Proposed configuration surface

Extend (do not break) existing vars:

| Name | Values | Notes |
| --- | --- | --- |
| `VISUAL_RECAP_AGENT` | `claude` \| `codex` \| **`opencode`** \| **`vibe`** \| (`agy` later) | Default becomes `opencode` once Mistral is configured |
| `VISUAL_RECAP_MODEL` | e.g. `mistral/mistral-medium-latest` | Same shape as `CS_AGENT_MODEL` for OpenCode |
| `ENABLE_MISTRAL` / `ENABLE_GOOGLE` | reuse from CodeScene | Gate OpenCode providers |
| Secrets | `MISTRAL_API_KEY`, `PLAN_RECAP_TOKEN` (+ optional `GOOGLE_API_KEY`) | `PLAN_RECAP_TOKEN` still required regardless of agent |

Gate changes (presence-only, never log secret values):

```text
HAS_MISTRAL  = secrets.MISTRAL_API_KEY != ''
HAS_PLAN     = secrets.PLAN_RECAP_TOKEN != ''   # already present
agent=opencode → require HAS_MISTRAL (or Google if ENABLE_GOOGLE)
agent=vibe     → require HAS_MISTRAL
agent=agy      → require HAS_ANTIGRAVITY (Phase 2)
```

## Phase 1 implementation sketch (OpenCode)

Reuse CodeScene’s provider resolution almost verbatim:

1. **Resolve providers / model** step → outputs `enable_mistral`, `model`
   - Prefer `vars.VISUAL_RECAP_MODEL`, else `mistral/mistral-medium-latest`
2. **Configure OpenCode auth** → `~/.local/share/opencode/auth.json`
3. **Install OpenCode** (pin version; same channel CodeScene action uses, or
   `npm i -g opencode-ai` / official install — **verify pin before merge**)
4. **Run agent**:

```bash
# Pseudocode — exact CLI flags to verify against OpenCode docs during impl
opencode run \
  --model "$MODEL" \
  --prompt "$(cat recap-prompt.md)" \
  # must be able to Write ./recap-source.json; deny network except model API
```

5. Retry once if `recap-source.json` missing (same as Claude/Codex steps)
6. Keep publisher / screenshot / comment steps unchanged
7. `agent-summary` / usage: pass `opencode` + result log file if format differs;
   soft-fail usage upload like today

Security (align with existing recap hardening):

- Still `pull_request` (not `pull_request_target`)
- `persist-credentials: false`
- Tool allowlist: Read + Write(workspace) + `git diff` only — no broad shell
- Never interpolate PR body into shell; prompt already built via `RECAP_CLI`
- Do not log `MISTRAL_API_KEY`

## Phase 1b sketch (Vibe)

```bash
export MISTRAL_API_KEY  # from secrets, env only
vibe --prompt "$(cat recap-prompt.md)" \
  --agent auto-approve \
  --output json \
  > vibe-result.json 2> vibe-stderr.log
# Confirm Vibe writes recap-source.json when instructed by the prompt;
# if not, add an explicit “write the plan MDX to recap-source.json” constraint
# in build-prompt or a thin wrapper.
```

Install: pin `uv tool install mistral-vibe==<version>` (no curl\|bash in CI).

## Phase 2 sketch (Antigravity) — spike only

Blockers to resolve in a spike PR:

1. Auth: document exact env (`ANTIGRAVITY_API_KEY` vs token) that works headless
2. Stdout: PTY via `script -qec 'agy …' /dev/null` until #76 is fixed upstream
3. Approvals: `--headless` / `--approve` policy that allows Write of
   `recap-source.json` without hanging
4. Cost: confirm this does **not** silently burn payg Gemini

Until those four are proven, keep `agy` out of the default agent list.

## Migration plan for this repo

1. Add `PLAN_RECAP_TOKEN` (and optional `PLAN_RECAP_APP_URL`) — required today
2. Implement `opencode` agent path + gate updates + README
3. Set repo vars: `VISUAL_RECAP_AGENT=opencode`,
   `VISUAL_RECAP_MODEL=mistral/mistral-medium-latest` (or your preferred model)
4. Smoke on a non-draft PR; confirm sticky recap comment + artifact
5. Optionally add `vibe` path; A/B which meter you prefer
6. Defer Antigravity until spike checklist passes

## Out of scope / non-goals

- Replacing the Plan publisher or screenshot pipeline
- Running untrusted PR-head agent CLIs
- Making Antigravity the default without a green CI spike
- Changing CodeScene’s provider defaults (already Mistral-first)

## Open questions for you

1. Does your existing `MISTRAL_API_KEY` draw from **Pro/Vibe included quota**, or
   separate **API pay-as-you-go**? That decides default `opencode` vs `vibe`.
2. Should Google stay available as OpenCode fallback (`ENABLE_GOOGLE`) for
   visual recap, or Mistral-only?
3. Want Antigravity as an explicit Phase 2 spike issue, or drop it for now?

## Decision ask

Approve **Phase 1 = OpenCode + Mistral** (mirror CodeScene) to implement next,
with optional **Vibe** as `VISUAL_RECAP_AGENT=vibe` if Pro metering prefers it.
