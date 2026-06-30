# PR Triage — 2026-06-30

## Duplicate & overlap analysis

### Closed as superseded (session-doc consolidation)

| Closed | Reason |
|--------|--------|
| pc #1369, #1370, #1375, #1376, #1382, #1383 | Stale cursor-agent session-report drafts consolidated into 2026-06-30 run |

### Closed → salvage replacement (DIRTY after merge burst)

| Old PR | Salvage draft | Overlap |
|--------|---------------|---------|
| pc #1402 | #1433 | parse_inventory main() tests |
| pc #1424 | #1434 | get_duplicates tests |
| pc #1397 | #1435 | _find_matching_prs tests |
| pc #1393 | #1436 | create_denylist tests |
| pc #1391 | #1437 | format_lists error paths |
| pc #1407 | #1438 | process_allowlist_files mocks |
| esp #1168 | #1192 | Palette fallback instructions |
| esp #1175 | #1193 | NLP transformer core tests |
| esp #1191 | #1194 | forgiving CLI provider selection |

### Related clusters (not closed)

| Cluster | PRs | Notes |
|---------|-----|-------|
| pc test_create_consolidated_lists | #1393 (salvaged #1436), #1407 (salvaged #1438) | Both touch same test file; salvaged separately — review for overlap before merging both |
| esp Palette UX | #1192, #1194 | Distinct files (app_runner vs setup_wizard); merge sequentially |

## Merge ordering applied

1. **Security** — pc #1416 (Sentinel)
2. **Code health / logging** — esp #1177, #1173
3. **Tests** — esp #1172, #1174, #1176; then pc test/refactor cluster (#1387–#1421)
4. **Performance** — pc #1409, #1425–#1427
5. **UI** — pc #1428
6. **Re-validate siblings** after each merge (Lesson 0cs) — cascade produced 9 DIRTY PRs salvaged

## Blockers identified

| Blocker | Affected PRs | Type | Next step |
|---------|--------------|------|-----------|
| CodeScene code health | pc #1422, esp #1179 | PR-specific | `/cs-agent` posted; re-check after remediation |
| GitGuardian Security Checks | pc #1398 | security scan | DEFER — investigate flagged content before merge |
| Trunk Merge Queue | pc #1432, esp #1180, #1190 | infra/MQ | DEFER — not blocking salvage drafts |
| DIRTY conflict | esp #1179 | merge conflict | Salvage after CodeScene remediation or manual rebase |

## Security gate notes

- 27 merges passed Gate 2 (no secrets, no permission escalation detected in diffs).
- esp salvage drafts (#1192–#1194) are **draft** per security-classified repo policy (Lesson 0bb).
- pc #1398 GitGuardian failure requires human review before any merge.
