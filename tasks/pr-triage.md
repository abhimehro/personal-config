# PR triage — 2026-03-27

| Repo | PR # | Category | Duplicate / stale | Disposition | Rationale |
| ---- | ---: | -------- | ----------------- | ----------- | ----------- |
| personal-config | 682 | SECURITY | None | **MERGED** (squash) | CWE-377 LaunchAgent log paths; checks green. **Auto-fix:** restored `.trunk/plugins/trunk` symlink to match `main` (Jules had pointed it at a runner-local path). |
| personal-config | 681 | CI/INFRA | None | **ESCALATE / hold** | Merge conflicts with `main`; daily QA batch — human rebase + review. |
| personal-config | 678 | CI/INFRA | None | **ESCALATE** | Draft workflow consolidation — CI trust boundary; verify action pins and `permissions:`. |
| personal-config | 677 | SECURITY | Superseded by #682 | **CLOSED** | Same plist fix as #682; redundant sentinel doc + conflicts. |
| ctrld-sync | 672 | SECURITY | None | **MERGED** | URL length cap in `validate_folder_url`; checks green. |
| ctrld-sync | 669 | CI/INFRA | None | **ESCALATE** | Draft workflow consolidation. |
| ctrld-sync | 668 | SECURITY | Superseded by #672 | **CLOSED** | Same URL limit intent; conflicting + #672 merged. |
| email-security-pipeline | 587 | CI/INFRA | None | **MERGED** | Fix invalid `<version>` placeholder in pre-commit config; checks green. |
| email-security-pipeline | 592 | PERFORMANCE | None | **MERGED** | File signature detection optimization; checks green. |
| email-security-pipeline | 596 | UI | None | **MERGED** | CLI spinner / a11y; checks green. |
| email-security-pipeline | 597 | SECURITY | None | **MERGED** | Attachment detection bypass; checks green; merge before closing #585. |
| email-security-pipeline | 594 | CI/INFRA | None | **ESCALATE** | Draft; 14 workflow files — human review required. |
| email-security-pipeline | 593 | CI/INFRA | No-op | **CLOSED** | `changedFiles == 0`; QA narrative only. |
| email-security-pipeline | 585 | SECURITY | Obsolete vs main after #597 | **CLOSED** | Conflicted; superseded by merged attachment hardening. |
| Seatek_Analysis | 106 | SECURITY | None | **MERGED** | Redact exception details in logs; checks green. |
| Seatek_Analysis | 107 | PERFORMANCE | None | **MERGED** | Vectorized correction application; checks green (merged after #106). |
| Hydrograph_Versus_Seatek_Sensors_Project | 93 | PERFORMANCE | None | **MERGED** | Micro-optimizations; checks green. |
| Hydrograph_Versus_Seatek_Sensors_Project | 94 | SECURITY | None | **MERGED** | Centralize `sanitize_filename`; checks green (merged after #93). |

## Automation expansion (policy)

Included when **any** of: `author.is_bot`, branch matches `jules/*`, `sentinel-*`, `bolt/*`, `palette/*`, `automation-*`, `daily-qa-*`, `chore/jules-*`, or body/footer references Jules / automated QA.

## Merge ordering (executed)

1. email-security-pipeline: 587 → 592 → 596 → 597 (dependency/UI before security parser change).  
2. personal-config: 682 (after symlink fix).  
3. ctrld-sync: 672.  
4. Seatek_Analysis: 106 → 107.  
5. Hydrograph: 93 → 94.  

After each batch, remaining PRs were re-checked for mergeability (API `mergeable` / `mergeStateStatus`).
