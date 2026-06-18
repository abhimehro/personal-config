# Security remediation master tracker (ABHI-950)

Living status board for the
[Security Remediation Sprint](https://linear.app/abhis-space/project/security-remediation-sprint-3346e8289f29).\
Canonical agent instructions:
[docs/AI_AGENT_SECURITY_REMEDIATION_GUIDE.md](../docs/AI_AGENT_SECURITY_REMEDIATION_GUIDE.md).

**Last updated:** 2026-05-24 (ABHI-967 — personal-config agent pass)

---

## Urgent — Cursor

| ID       | Title                                             | Repo                    | Status                    | Notes                                                              |
| -------- | ------------------------------------------------- | ----------------------- | ------------------------- | ------------------------------------------------------------------ |
| ABHI-918 | Rotate live credentials / remove committed WebDAV | multi                   | **Human action required** | Repo placeholders done; PAT/WebDAV rotation in GitHub + 1Password  |
| ABHI-954 | Rotate GitHub PAT                                 | —                       | Pending human             |                                                                    |
| ABHI-965 | Rotate WebDAV password                            | —                       | Pending human             |                                                                    |
| ABHI-964 | Verify no hardcoded credentials                   | personal-config         | **In progress**           | `tests/test_repo_credential_hygiene.sh`                            |
| ABHI-943 | Script injection — copilot-setup (email-security) | email-security-pipeline | Open                      | See ABHI-966, ABHI-956                                             |
| ABHI-929 | Script injection — copilot-setup                  | personal-config         | **Done**                  | `copilot-setup-steps.yml` + `tests/test_copilot_setup_workflow.py` |
| ABHI-963 | Fix copilot-setup env binding                     | personal-config         | **Done**                  | Same PR as ABHI-929                                                |
| ABHI-955 | Verify matches summary.yml pattern                | personal-config         | **Done**                  | Regression test added                                              |
| ABHI-956 | Test malicious payload                            | email-security-pipeline | Open                      |                                                                    |
| ABHI-967 | AI Agent Security Remediation Guide               | docs                    | **Done**                  | This guide + tracker                                               |

---

## High — Devin

| ID                  | Title                           | Status                                                                                           |
| ------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------ |
| ABHI-951            | Safe spreadsheet export utility | Open                                                                                             |
| ABHI-952            | Audit workflow_dispatch inputs  | Open                                                                                             |
| ABHI-931 / ABHI-930 | Formula injection               | Open                                                                                             |
| ABHI-919            | Actions supply chain            | Partial — see [security-remediation-plan-2026-05-01.md](security-remediation-plan-2026-05-01.md) |
| ABHI-920            | Docker reproducibility          | Partial                                                                                          |
| ABHI-921            | Hardcoded paths                 | Partial                                                                                          |

---

## Medium / Low — Devin

| ID           | Title                                   | Status |
| ------------ | --------------------------------------- | ------ |
| ABHI-922–924 | Symlink, maintenance, media credentials | Open   |
| ABHI-953     | Security CI pipeline                    | Open   |
| ABHI-925     | AdGuard robustness                      | Open   |

---

## PR log (personal-config)

| PR              | Issues                                 | Summary                                                                |
| --------------- | -------------------------------------- | ---------------------------------------------------------------------- |
| _(this branch)_ | ABHI-967, ABHI-950, ABHI-929, ABHI-964 | Agent guide, tracker, CWE-94 regression tests, credential hygiene test |

---

## Blockers

- **Credential rotation (ABHI-918):** Cannot be completed by agents without
  access to GitHub PAT settings or 1Password vaults. Run verification tests
  after human rotation.
