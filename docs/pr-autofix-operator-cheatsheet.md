# PR Autofix Operator Cheat Sheet

This cheat sheet keeps PR Autofix runs consistent across:

- `personal-config`
- `email-security-pipeline`
- `ctrld-sync`

It assumes:

- You are using the `pr-autofix` skill.
- You want `autofix(<category>): PR #N (cycle K) -- …` subjects with trailers.

---

## 1. Commit message shape

**Subject:**

```text
autofix(<category>): PR #<n> (cycle <k>) -- <short outcome>
```

Examples:

- `autofix(Sentinel): PR #42 (cycle 1) -- tighten SSH config`
- `autofix(Bolt): PR #17 (cycle 2) -- reduce IMAP scans`

**Body (template):**

```text
Context:
- PR: #<n>
- Category: <Sentinel|Bolt|Palette>
- Inputs: <Copilot,Gemini,Human>

Changes:
- <what changed + where>

Verification:
- <what you ran / what to expect>

Notes:
- <needs human decision / trade-offs>

Autofix-PR: #<n>
Autofix-Cycle: <k>
Review-Inputs: Copilot,Gemini,Human
Mode: T2+S+H
```

`.gitmessage` at repo root contains this layout and can be used as your commit template.

---

## 2. Optional: use the commit template

From this repo:

```bash
# One-time setup (example; adjust path as you prefer)
mkdir -p ~/.config/git
ln -sf "$(pwd)/.gitmessage" ~/.config/git/commit-template.personal-config.txt
git config --global commit.template ~/.config/git/commit-template.personal-config.txt
```

You can symlink the same `.gitmessage` into other repos if you want a single source of truth.

---

## 3. Optional: gentle hook for Autofix trailers

A **non-blocking** `commit-msg` hook is provided at:

- `scripts/git-hooks/autofix-trailers-commit-msg.sh`

Install it in this repo with:

```bash
mkdir -p .git/hooks
ln -sf ../../scripts/git-hooks/autofix-trailers-commit-msg.sh .git/hooks/commit-msg
chmod +x scripts/git-hooks/autofix-trailers-commit-msg.sh
```

Behavior:

- Only runs special logic when the subject starts with `autofix(`.
- If no `Autofix-PR:` trailer is found:
  - Prints a reminder to stderr with the recommended trailers.
  - **Does not** block the commit.

---

## 4. Decision gates for PR Autofix cycles

Use this as a quick mental checklist before committing/pushing:

```text
- [ ] Have I coalesced all Critical/Should-fix review items into a single plan?
- [ ] Is this clearly Cycle 1 or Cycle 2 for this PR?
- [ ] Did I run the right repo-specific checks (e.g., nm-regress, tests, linters)?
- [ ] Does the commit message match: "autofix(<category>): PR #N (cycle K) -- …"?
- [ ] Did I fill in Autofix-PR / Autofix-Cycle / Review-Inputs / Mode trailers?
- [ ] Am I keeping to one push per cycle (barring critical hotfixes)?
```

If any of these are “no,” pause and fix that first—then run Autofix.
