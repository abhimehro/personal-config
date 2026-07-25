# PR Triage — 2026-07-25 (Phase 1)

## Classification rules applied

- Security / auth / secrets / TOCTOU / SSRF / tip-release majors → **ESCALATE**
- Sibling Sentinel env-filter PRs → escalate all (Lesson 0ej)
- Dependabot majors despite soft titles → escalate (Lesson 0ek)
- `dummy_todos.py` auth/DoS → escalate (Lesson 0ef)
- Routine Bolt/Palette/docs/test CI hygiene with green CI → **MERGE**
- Zero-diff Daily QA → remove from queue (prefer CLOSE; this run squash-merged empty #290)
- Draft docs/deps that are clearly safe → mark ready + MERGE
- Junk root harness (`test_perf.py`) → **AUTOFIX** then MERGE (Lesson 0e)

## Disposition plan

### MERGE

| PR | Reason |
|----|--------|
| pc #1770 | Bolt regex precompile; green |
| pc #1768 | Test-only sleep removal; green |
| esp #1356 | Palette UX hint; green |
| esp #1348 | Draft docs AGENTS stale note → ready + merge |
| hg #411 | Draft numpy bound align with poetry → ready + merge |
| hg #414 | Bolt opt after autofix remove `test_perf.py` |
| sc #290 | Zero-diff Daily QA (removed via squash; prefer close next time) |

### AUTOFIX

| PR | Fix |
|----|-----|
| hg #414 | Removed root `test_perf.py`; kept validator.py change |

### ESCALATE (Phase 2)

| PR | Reason |
|----|--------|
| pc #1766 | SSRF / safe_http trust boundary (later CONFLICTING) |
| pc #1767 | GH_TOKEN / source removal security |
| pc #1769 | ensure_gh_token hardening sibling |
| pc #1748 | visual-recap salvage |
| pc #1721 | CONFLICTING + env/token sensitivity |
| cs #1060 | Sentinel exception chaining |
| esp #1353/#1328 | TOCTOU cluster |
| esp #1319 | gh_token_cli |
| esp #1324/#1359 | Auth-Results scoring (+ junk patch script on #1359) |
| esp #1342 | IMAPClient API |
| Seatek #507/#518/#525 | Sentinel env-filter siblings |
| Seatek #521 | pandas major |
| Seatek #511 | Devin + Trunk FAIL |
| hg #413 | Sentinel DoS + CodeScene FAIL (`/cs-agent` posted) |
| sc #268/#275/#276/#285 | dummy_todos auth/DoS (+ CodeScene on #285) |
| rpce #126/#127 | artifact action tip majors |

### Duplicate / overlap groups

1. **Seatek Sentinel env** — #507, #518, #525 (keep all escalated; human picks)
2. **esp TOCTOU** — #1353, #1328
3. **esp Auth-Results** — #1324, #1359
4. **pc token helpers** — #1767, #1769
5. **sc dummy_todos** — #268, #275, #276, #285
6. **rpce artifact majors** — #126, #127

### Stale (>30d)

None this session (oldest in-scope age ≈ 8d: rpce #126/#127).
