# GitHub PAT rotation runbook (ABHI-954)

Linear: **ABHI-954** — Rotate GitHub PAT in GitHub settings

## Why

TruffleHog reported a **verified live GitHub PAT** in local `GH_TOKEN.env` under
`email-security-pipeline` (gitignored, never committed). Until the token is
revoked in GitHub, anyone with a copy of that file can act as your account
within the token’s scopes.

## Trust boundary

| Zone                                   | Risk                                               |
| -------------------------------------- | -------------------------------------------------- |
| GitHub → Settings → Developer settings | Only you can revoke/create tokens                  |
| Local `GH_TOKEN.env`                   | File on disk; treat as compromised after exposure  |
| Repo `secrets.GH_TOKEN` (Actions)      | Separate credential; rotate if it was the same PAT |

## Step 1 — Revoke the exposed token (GitHub UI)

1. Open
   [GitHub → Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens).
2. Identify the token that matches the leaked file (note name, last used,
   scopes).
3. **Delete / revoke** that token immediately.
4. Review [Security log](https://github.com/settings/security-log) for unusual
   API activity while the old token was valid.

Fine-grained PAT: use **Fine-grained tokens**. Classic PAT: use **Tokens
(classic)**.

## Step 2 — Create a replacement (least privilege)

Create a **new** token with only what automation needs:

| Use case                      | Suggested scopes                                                              |
| ----------------------------- | ----------------------------------------------------------------------------- |
| Local `gh` + PR scripts       | `repo`, `read:org`, `workflow` as needed                                      |
| `repository-automation-*.yml` | Match `.github/repository-automation.md` (`contents:read`, `issues:write`, …) |
| Read-only inventory           | `contents:read`, `pull_requests:read`                                         |

Prefer **fine-grained** tokens limited to required repositories.

## Step 3 — Store the new secret outside the repo

Do **not** commit the token. Preferred locations (pick one):

1. **GitHub CLI (recommended for local dev)**
   ```bash
   gh auth login -h github.com
   export GH_TOKEN="$(gh auth token)"   # session only; optional
   ```

2. **XDG config (file outside repo tree)**
   ```bash
   mkdir -p ~/.config/personal-config
   chmod 700 ~/.config/personal-config
   # Edit ~/.config/personal-config/GH_TOKEN.env — mode 0600
   export GH_TOKEN_ENV_FILE=~/.config/personal-config/GH_TOKEN.env
   ```

3. **1Password** (project standard)\
   Inject at runtime with `op run` / `op inject`; never write plaintext to the
   repo.

4. **Legacy path (deprecate)**\
   `../email-security-pipeline/GH_TOKEN.env` is still read as a fallback by
   `gh_token_env.py`, but you should **move** the file to
   `~/.config/personal-config/` and delete the old copy after rotation.

File format (single line is enough):

```bash
export GH_TOKEN=github_pat_...
```

## Step 4 — Update GitHub Actions secrets (if applicable)

If the leaked PAT was also stored as a repository or organization secret:

1. Repo → **Settings → Secrets and variables → Actions**
2. Update **`GH_TOKEN`** (used by `repository-automation-daily.yml`,
   `jules-daily-qa.yml`, etc.)
3. Re-run failed workflows or wait for the next schedule

Use a **dedicated** automation token for CI; do not reuse a personal laptop PAT
when avoidable.

## Step 5 — Verify (no secret output)

From `personal-config` repo root:

```bash
chmod +x scripts/ensure_gh_token.sh scripts/verify_gh_auth.sh
./scripts/verify_gh_auth.sh
```

Optional secret scan (requires TruffleHog installed):

```bash
trufflehog filesystem . --only-verified
```

Expect **no verified GitHub PATs** under tracked paths. Local gitignored files
must be rotated separately (Step 1).

## Step 6 — Hygiene checklist

- [ ] Old PAT revoked in GitHub settings
- [ ] New PAT created with minimal scopes
- [ ] Local file updated or removed; prefer
      `~/.config/personal-config/GH_TOKEN.env`
- [ ] `secrets.GH_TOKEN` updated if it shared the same value
- [ ] `./scripts/verify_gh_auth.sh` succeeds
- [ ] No scripts use `source …/GH_TOKEN.env` (use `scripts/ensure_gh_token.sh`
      instead)

## Code references

- `gh_token_env.py` — safe env-file parsing for Python automation
- `scripts/ensure_gh_token.sh` — shell entrypoint without `source`
- `.gitignore` — `GH_TOKEN.env` at repo root
- `tasks/security-remediation-plan-2026-05-01.md` — Issue 1 tracking

## Related

- [Credential rotation (general)](CREDENTIAL_ROTATION.md)
- [GitHub App / PAT checklist](github-app-pr-automation-checklist.md) §4
