# PR Triage — 2026-05-29

**Preflight:** PASS (6/6)  
**Disposition key:** MERGE · DEFER · CLOSE-SUPERSEDED · ESCALATE

## Duplicate / overlap groups

| Group | Keeper | Action on others |
| --- | --- | --- |
| ESP workflow pinning vs bandit nosec | **#957** (infra pins) first | #956 rebase after #957; not duplicate — different file sets |

## Dispositions

| Disposition | PRs |
| --- | --- |
| **MERGE** | series #86; pc #1089 |
| **DEFER** | esp #957, esp #956 |
| **CLOSE-SUPERSEDED** | pc #1088 (after this session’s artifact PR lands) |

## Security review notes

| PR | Tier | Assessment |
| --- | --- | --- |
| series #86 | T1 Sentinel | `realpath` before `commonpath` closes symlink traversal bypass in config loader. Merged. |
| esp #956 | T3 | `# nosec` on intentional `subprocess` / SSL test helpers; valid if bandit job can run. Blocked by CI policy, not code gate. |
| esp #957 | CI/INFRA | Checkout/setup-python SHA pins align with org policy; incomplete until bandit composite deps pinned. |

## CI anomalies

| PR | Check | Root cause |
| --- | --- | --- |
| esp #956, #957 | pytest / bandit | Org requires full-length action SHAs; branch workflows still use `@v6` or composite pulls `@main` / `@v3` |
| pc #1089 | swift / bugbot pending | Non-blocking; required application checks passed |

## Human merge queue

| PR | Repo | Why human |
| --- | --- | --- |
| #957 | email-security-pipeline | Replace or fork `shundor/python-bandit-scan` workflow with fully pinned SARIF upload path |
| #956 | email-security-pipeline | Merge after infra unblocks CI |
