---
name: pr-autofix
description: >-
  PR Autofix skill for personal-config, email-security-pipeline, and ctrld-sync.
  Formalizes ingest → plan → implement → verify → commit/push → report.
  Coalesces reviewer feedback (Copilot/Gemini/humans) and throttles pushes to avoid review storms.
---

# PR Autofix (Security-First, Review-Coalescing)

## Purpose

Convert PR review feedback into a merge-ready PR—without opening new PRs or creating ongoing “follow-up tasks.”

This skill:

- Ingests review comments and CI results
- Proposes and implements fixes
- Pushes updates to the **existing PR branch**
- Reports back with a structured, auditable summary (ELIR-aligned)

## Scope / Repos

Targets:

- `personal-config`
- `email-security-pipeline`
- `ctrld-sync`

Best used on one PR at a time.

## Non-negotiable guardrails

- Never commit or paste secrets, tokens, credentials, PII, or other sensitive data.
- Never add new dependencies without explicit approval and dependency vetting.
- Never force-push unless explicitly approved.
- Never run destructive commands without explicit confirmation.
- If a change touches **auth/authorization, payments, schema changes, or migrations**: stop and request approval.

## Push throttling (prevents review storms)

### Principle

**One push per cycle**, not one push per comment.

### Rules

- Coalesce all feedback into a single fix plan **before** making edits.
- Push **at most once per cycle**, and only after verification is complete.
- If new review comments arrive mid-cycle:
  - Record them as “arrived during cycle”
  - Do not push again until the next cycle
- Default cooldown: **20–30 minutes** after a push, unless:
  - a security-critical fix is required, or
  - CI is failing due to a small, clearly related follow-up fix

### Cycle limit

- Max **2 cycles** without a human check-in.

## Required commit message format (autofix cycles)

**Subject**

```
autofix(<category>): PR #<n> (cycle <k>) -- <short outcome>
```

**Body**

```
Context:
- PR: #<n>
- Category: <Sentinel|Bolt|Palette>
- Inputs: Copilot review, Gemini review, CI

Changes:
- <what changed + where>

Verification:
- <what ran / what to expect>

Notes:
- <needs human decision / trade-offs>
```

**Optional trailers (strongly recommended)**

```
Autofix-PR: #<n>
Autofix-Cycle: <k>
Review-Inputs: Copilot,Gemini,Human
Mode: T2+S+H
```

Use the repo’s `.gitmessage` and the optional `scripts/git-hooks/autofix-trailers-commit-msg.sh` hook to keep trailers consistent without blocking normal commits.

## Workflow (ingest → plan → implement → verify → commit/push → report)

### 0) Pre-flight (must pass before edits)

- Confirm you’re on the PR branch.
- Confirm the workspace is clean (or only contains intended changes).
- Confirm the PR category (Sentinel/Bolt/Palette) from title/labels/prefix.

### 1) Ingest

Collect and normalize inputs:

- PR intent (title/description)
- Diff overview (which files changed)
- Review comments (Copilot/Gemini/humans)
- CI checks (pass/fail + key failures)

De-duplicate feedback by:

- file/function + issue type

Classify each item:

- **Critical** (blocker)
- **Should-fix** (merge-prep)
- **Nit** (optional)

### 2) Plan (before editing)

Provide a fix plan in **≤7 bullets**:

- Address all **Critical** and **Should-fix** items
- Explicitly flag “Needs human decision” items
- State whether this is **Cycle 1** or **Cycle 2**

### 3) Implement

Implement minimal diffs:

- Prefer small, focused changes
- Preserve existing behavior unless explicitly required
- Update docs/journals when inaccurate or misleading
- Add/update tests if changes introduce or fix edge-case logic

### 4) Verify (safe)

Run only checks that exist in the repo.

If you’re unsure a command exists, mark it “if present” and suggest the closest alternative.

Record:

- what you ran
- what passed/failed

### 5) Commit + Push (throttled)

- Create **exactly one commit per cycle** unless there’s a strong audit reason to split (e.g., security fix vs. refactor).
- Use the required commit message format.
- Push to the existing PR branch.
- Do not force-push without approval.
- Do not push more than once per cycle.

### 6) Report (must be `T2+S+H`)

Always respond using:

```markdown
Route: T2+S+H

## Summary

- Repo:
- PR:
- Branch:
- Primary mode:
- Cycle:
- What changed:

## Checklist

- [ ] Correctness:
- [ ] Security:
- [ ] Performance:
- [ ] Maintainability:
- [ ] Testing:

## Categorized Findings (post-fix)

### Security

### Performance

### Aesthetics / Clarity

## Mapping: Review Comment → Fix

- Comment source:
- Comment:
- Fix:
- Files:

## Push Control

- Pushes this cycle: 0 or 1
- Cooldown recommendation:
- New comments observed mid-cycle: Yes/No

## ELIR

- PURPOSE:
- SECURITY:
- FAILURE MODES:
- VERIFY:
- MAINTAIN:

## Stop conditions

Stop when:

- No remaining Critical items
- CI is green (or failures are explained and unrelated)
- Remaining items are nits you explicitly accept
```
