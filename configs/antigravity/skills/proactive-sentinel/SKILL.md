---
name: proactive-sentinel
description: Deep code-level security and trust-boundary audit reusing per-repo .jules/sentinel.md memory. Use for scheduled or manual proactive security sweeps across repositories.
---

# Proactive Sentinel (Security and Trust-Boundary Lens)

Run a high-signal, code-level security review focused on concrete exploit or
failure mechanisms rather than generic scanner noise.

## Mandatory Public-Repository Disclosure Rule

All target repositories in `$HOME/dev/` are public on GitHub.

1. **Read-only journal consultation before fix:** Read
   `<repo>/.jules/sentinel.md` (if present) and `<repo>/AGENTS.md` before
   scanning so previously resolved CWE patterns and intentional architecture
   choices are respected.
2. **Never write pre-merge findings to `.jules/sentinel.md`:** Appending
   unpatched CWE details to a tracked file in a public repository discloses the
   vulnerability before a fix is merged. The `PreToolUse` safety hook
   (`proactive-guard.py`) enforces this rule.
3. **Permanent exclusion from public Draft PRs (`2A`):** Even after `bolt`,
   `palette`, and `code-health` graduate to Draft PRs, `proactive-sentinel`
   findings **never** open public Draft PRs or issues (a public Draft PR still
   exposes the vulnerability diff before merge). Keep findings local-only in
   `$HOME/.gemini/antigravity/proactive-reports/YYYY-MM-DD-<repo>.md`
   (`chmod 600`), and route remote fixes manually through a **GitHub Security
   Advisory temporary private fork**.
4. **Verified post-merge journal update only:** After the security fix has
   merged to the default branch, unlock a 5-minute repo-scoped lease via:
   `$HOME/dev/personal-config/scripts/antigravity-proactive-ctl.sh sentinel-post-merge --repo <repo> --pr <merged_pr_number>`
   before appending the prevention lesson to `<repo>/.jules/sentinel.md`.

## Hard Boundaries

- Never modify authentication flows, credential storage, payment logic, database
  schemas, or live macOS `launchd` / DNS / VPN state unattended.
- Never print, log, or echo secret values, tokens, SSH material, or `.env`
  contents.
- Never open a public pull request or issue containing exploit details or
  security diffs for an unmerged finding.

## Audit Checklist

Prioritize changes and reachable code paths across these categories:

1. **Command and Argument Injection:**
   - Unquoted shell expansions, `eval`, `bash -c` string concatenation with
     untrusted inputs, or missing `--` end-of-options markers before positional
     paths/URLs.
   - GitHub Actions workflows interpolating `${{ github.event.* }}` directly
     inside `run:` blocks instead of binding through `env:`.
2. **Path Traversal and Symlink Safety:**
   - Archive extraction, file-sync targets, or user/config path resolution
     lacking canonical parent checks (`Path.resolve()` containment).
   - Predictable `/tmp` filenames without `mktemp` or `0600`/`0700` permissions
     on credential or report outputs.
3. **Credential and Environment Leakage:**
   - Subprocesses inheriting `SSH_AUTH_SOCK`, `GH_TOKEN`, `GITHUB_TOKEN`, or API
     keys when running untrusted or third-party checks.
   - Bash indirect variable expansion (`${!var}`) used on secret labels that may
     contain spaces instead of `printenv`.
4. **Network and Daemon Exposure:**
   - Local servers or debug endpoints binding to `0.0.0.0` instead of
     `127.0.0.1`.
   - Unsafe HTTP redirects, missing TLS verification, or unbounded timeouts on
     external API calls.

## Execution Workflow

1. Inspect `<repo>/AGENTS.md` and `<repo>/.jules/sentinel.md`.
2. Review recent commits (`git -C <repo> log -n 20 --oneline`) and open PRs to
   avoid duplicating active work.
3. Identify at most **one** concrete **High** or **Warning** finding with a
   verifiable code path, CWE mapping, and minimal remediation. If no concrete
   issue exists, record a clean no-op pass.
4. For code-fixable findings that do not cross hard boundaries:
   - Prepare an isolated local worktree:
     `$HOME/dev/personal-config/scripts/proactive-worktree.sh prepare --repo-path <repo> --lens sentinel --mode local`
   - Apply the minimal fix inside the worktree without editing test or build
     harnesses unless explicitly authorized.
   - Run verification:
     `$HOME/dev/personal-config/scripts/proactive-worktree.sh verify --worktree <worktree_path> --lens sentinel`
     Verification enforces an AST parse + undefined-name (F82) floor on touched
     Python files and a base-relative test-coverage gate, so a security fix that
     drops test coverage blocks (`exit 2`) even when the suite stays green. A
     hardening change that legitimately removes a now-invalid test must declare
     the new total with `--expected-test-count <n>` and say so in the report.
5. Write the local report (`Status: SECURITY_REPORT_ONLY`) to
   `$HOME/.gemini/antigravity/proactive-reports/YYYY-MM-DD-<repo>.md`
   (`chmod 600`) with file/line references, CWE ID, failure mechanism,
   verification output, local worktree path, and private GitHub Security
   Advisory remediation steps.
