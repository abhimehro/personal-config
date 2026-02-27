# GitHub App Permission Checklist for PR Automation

This checklist configures a GitHub App (or equivalent token-backed automation identity) so AI agents can triage and resolve bot-authored PR backlogs across repositories with least privilege.

## 1) Installation Scope

- [ ] Install the app on every target repository.
- [ ] Use one app installation per trust domain:
  - Personal projects: `personal-config`, `email-security-pipeline`, `ctrld-sync`
  - Academic/research repos: separate installation (recommended)
- [ ] Keep personal and research installations isolated (separate tokens, separate operational logs, separate policy defaults).

## 2) Required Repository Permissions

Set these repository-level permissions for the app:

- [ ] **Pull requests: Read & write**
- [ ] **Issues: Read & write** (PR conversation comments use issue comment APIs)
- [ ] **Contents: Read & write** (merge and branch cleanup paths)
- [ ] **Actions: Read**
- [ ] **Checks: Read**
- [ ] **Commit statuses: Read**
- [ ] **Metadata: Read** (default)

Optional (only if you need agent-driven auto-merge management):

- [ ] Allow enabling auto-merge through policy + app permissions where available.

## 3) Branch Policy Alignment

- [ ] Confirm required status checks are consistent and stable across repos.
- [ ] Decide merge policy per repo:
  - Human-supervised merge only (strictest)
  - Agent can merge when all checks pass
  - Agent can enable auto-merge (if policy permits)
- [ ] Avoid blanket admin bypass for automation unless explicitly required.

## 4) Token Handling & Runtime Injection

- [ ] Store token as a secret in your runtime/secrets manager.
- [ ] Inject as `GH_TOKEN` in the agent environment at startup.
- [ ] Never commit token values to repo files.
- [ ] Rotate token regularly and on any suspected leak.

## 5) Preflight Validation (Fail Fast)

Use the preflight script before each triage session:

```bash
bash scripts/preflight-gh-pr-automation.sh \
  --repo abhimehro/personal-config \
  --repo abhimehro/email-security-pipeline \
  --repo abhimehro/ctrld-sync
```

For full write-path verification (recommended), use dedicated probe PRs and explicit write probes:

```bash
bash scripts/preflight-gh-pr-automation.sh \
  --repo abhimehro/personal-config \
  --repo abhimehro/email-security-pipeline \
  --repo abhimehro/ctrld-sync \
  --require-write-probes \
  --probe-pr abhimehro/personal-config#<open_probe_pr_number> \
  --probe-pr abhimehro/email-security-pipeline#<open_probe_pr_number> \
  --probe-pr abhimehro/ctrld-sync#<open_probe_pr_number>
```

## 6) Probe PR Guidance

- [ ] Keep one open "automation probe" PR per repo for capability checks.
- [ ] Expect preflight write-probe mode to add a comment/review and temporarily close/reopen that probe PR.
- [ ] Do not use production-critical PRs as probes.

## 7) Operational Runbook Notes

- If preflight fails on:
  - `addComment` / `addPullRequestReview`: increase **Issues**/**Pull requests** write scope.
  - `closePullRequest`: increase **Pull requests** write scope.
  - `enablePullRequestAutoMerge`: update branch policy and app capabilities for auto-merge.
- If one repo passes and others fail, compare app installation scope and branch rulesets repo-by-repo.
