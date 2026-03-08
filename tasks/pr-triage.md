# PR Triage Findings

Triage basis: live session 4 inventory from `tasks/pr-inventory.md` (2026-03-08).

## Exact Duplicates / High File Overlap

No exact duplicates detected in the current open Jules queue.

## Overlap / Merge-Ordering Risks

| Repo | PRs | Shared Files | Keep / Order | Rationale |
|---|---|---|---|---|
| abhimehro/[REDACTED]-config | #615, #618 | `maintenance/bin/node_maintenance.sh` | Merge #615 first, then re-check #618 | Security fix for insecure temp files should land before the performance refactor touching the same block |
| abhimehro/[REDACTED]-config | #619, #620 | `media-streaming/archive/scripts/infuse-media-server.py` | Merge #620 first; require a narrowed diff for #619 | #620 is a safe dead-import cleanup; #619 includes broad formatting churn beyond the target optimization |
| abhimehro/ctrld-sync | #620, #623 | `main.py` | Merge #620 first, then rebase/re-check #623 | SSRF hardening is higher priority than the loop-optimization PR touching the same function area |
| abhimehro/ctrld-sync | #622, #623 | `tests/test_ux.py` | Strip the identical unrelated test hunk from at least one PR | The shared one-line test change is unrelated to both primary tasks and will create needless conflicts |

## Scope-Creep Findings

| Repo | PR # | Finding | Disposition Impact |
|---|---:|---|---|
| abhimehro/[REDACTED]-config | 614 | Adds `tasks/lessons.md` update unrelated to the test gap | MERGE-AFTER-FIX |
| abhimehro/[REDACTED]-config | 615 | Includes generated `.trunk/plugins/trunk` symlink churn | MERGE-AFTER-FIX |
| abhimehro/[REDACTED]-config | 619 | Includes `.jules/bolt.md`, generated `.trunk/plugins/trunk`, and broad quote-format churn in the target file | REQUEST-CHANGES |
| abhimehro/ctrld-sync | 622 | Includes unrelated `tests/test_ux.py` edit | MERGE-AFTER-FIX |
| abhimehro/ctrld-sync | 623 | Includes unrelated `.jules/bolt.md` and `tests/test_ux.py` changes | MERGE-AFTER-FIX |

## Security Gate Notes

| Repo | PR # | Security Result | Notes |
|---|---:|---|---|
| abhimehro/[REDACTED]-config | 615 | PASS with cleanup needed | Fix addresses predictable temp-file usage, but generated `.trunk` symlink must be removed before merge |
| abhimehro/[REDACTED]-config | 616 | PASS | Hash verification fails closed by deleting the download and falling back to a local build |
| abhimehro/[REDACTED]-config | 617 | PASS | `getent` fallback plus username allowlist reduces `eval` exposure |
| abhimehro/ctrld-sync | 620 | PASS | SSRF checks explicitly block loopback, private, unspecified, link-local, multicast, and CGNAT IPv4 |

## Stale Candidates (>30 days inactive and failing CI)

No stale candidates detected under the configured threshold.

## Ready-to-Execute Human Merge Queue

Because this environment treats `gh` as read-only and the repositories use Trunk-managed merge flows, no remote actions were executed here. Recommended order:

### abhimehro/[REDACTED]-config

1. **MERGE** `#617` — command injection fix in `get_user_home`
2. **MERGE** `#616` — binary integrity verification for Mole installer
3. **MERGE-AFTER-FIX** `#615` — remove `.trunk/plugins/trunk`, then merge the CWE-377 fix
4. **MERGE** `#618` — re-check against `#615`, then merge the `node_maintenance.sh` optimization
5. **MERGE** `#620` — unused import cleanup
6. **REQUEST-CHANGES** `#619` — narrow the diff to the actual perf change before merge consideration
7. **MERGE-AFTER-FIX** `#614` — drop the unrelated `tasks/lessons.md` edit
8. **MERGE** `#621` — `print_summary` refactor after the higher-priority items above

### abhimehro/email-security-pipeline

1. **MERGE** `#539` — clean `_validate_signature_match` optimization

### abhimehro/ctrld-sync

1. **MERGE** `#620` — SSRF hardening (re-check mergeability first)
2. **MERGE** `#621` — profile ID format tests (re-check mergeability first)
3. **MERGE-AFTER-FIX** `#622` — remove the unrelated `tests/test_ux.py` hunk
4. **MERGE-AFTER-FIX** `#623` — remove `.jules/bolt.md` and the unrelated `tests/test_ux.py` hunk, then rebase after `#620`
