# PR Triage — 2026-06-23

## Duplicate & overlap analysis

### Closed as duplicate

| Keeper | Closed | Overlap | Rationale |
|--------|--------|---------|-----------|
| hg #291 (merged) | hg #290 | `processor.py` np.where optimization | #291 included tests + pyproject; #290 was subset |
| sc #145 (merged) | sc #142 | `scripts/processor.py` Z-score vectorization | #145 had green CI; #142 blocked on CodeScene |

### Related clusters (not closed — distinct intent)

| Cluster | PRs | Notes |
|---------|-----|-------|
| personal-config Palette a11y | #1326, #1329 | #1326 adds `.codacy.yml` + ARIA; #1329 focuses screen-reader grouping. Merge sequentially after Codacy infra fix. |
| repoprompt-ce Changelog perf | #39, #49 | Both touch `Changelog.swift`; #39 extracts DateFormatter, #49 optimizes usage. Not >90% overlap — defer to salvage for ordering. |
| Hydrograph Bolt np.where | #290, #291 | Resolved: kept #291. |
| series_correction Bolt Z-score | #142, #145 | Resolved: kept #145. |

### Superseded

None identified beyond the two closures above. No stale (>30d) bot PRs in scope.

## Merge ordering applied

1. **Dependencies** — esp, Seatek, hg, sc, pc (#1331 codacy-action first)
2. **CI/QA fixes** — hg #289
3. **Performance/UI** — hg #291, sc #145, Seatek #358, esp #1140, Seatek #357
4. **Re-validate siblings** after each merge (Lesson 0cs)

## Blockers identified

| Blocker | Affected PRs | Type | Next step |
|---------|--------------|------|-----------|
| Codacy Security Scan fail | pc #1330–1337, #1324–1329 | main-side infra | ESCALATE: codacy-action bumped (#1331) but scan still fails on open PRs; investigate Codacy project config |
| CodeScene code health | ctrld #943 | PR-specific | `/cs-agent` posted; merge #943 then re-run dependabot cluster |
| mypy/ruff on main (pre-#943) | ctrld #938–942 | blocked by #943 | Merge #943 after CodeScene green |
| validate (numpy) | Seatek #351 | dependency constraint | DEFER — validate job fails on numpy >=2.5.0 bump |
| Style / build cluster | rpce #24–49 | salvage tail | Hand off to Phase 2 salvage agent |

## Security gate notes

- No secrets, permission escalation, or CVE regressions detected in merged PRs.
- rpce #41 (Keychain accessibility salvage) remains **ESCALATE** — security-sensitive; draft salvage PR.
- pc #1334 (workflow consolidation) **ESCALATE** — trust boundary (CI/INFRA); blocked on Codacy but warrants human review of workflow YAML integrity per Lesson 0cu.
