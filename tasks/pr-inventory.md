# PR Inventory — 2026-07-20 (Phase 2 salvage refresh)

**Preflight:** PASS 7/7 (+ `make cursor-cloud-hooks`)  
**Mode:** salvage (draft-only; never auto-merge)  
**Agent branch:** `cursor-agent/automated-pr-salvage-9b5e`  
**Input:** Phase 1 remainder from `tasks/pr-review-2026-07-20.md` + live re-fetch

| Repo | PR | Author | Title | Category | CI | Conflicts | Disposition |
|------|---:|--------|-------|----------|----|-----------|-------------|
| personal-config | 1670 | cursor | workflow consolidate ABHI-1321 | CI/INFRA | — | DIRTY | ESCALATE (0ea) |
| ctrld-sync | 1036 | Palette | `_print_hint()` empty states | UI | GREEN (CodeScene remediates) | CLEAN | READY human merge |
| email-security-pipeline | — | — | — | — | — | — | zero open |
| Seatek_Analysis | — | — | — | — | — | — | zero open |
| Hydrograph… | 374 | dependabot | numpy 2.2.6 | DEPENDENCY | GREEN | CLEAN | ESCALATE major |
| series_correction… | 233 | Jules | user authentication | SECURITY | GREEN | CLEAN | ESCALATE auth |
| repoprompt-ce | 132 | Bolt | DateFormatter static | PERFORMANCE | Style FAIL | CLEAN | CLOSED → salvage #133 |
| repoprompt-ce | 133 | cursor salvage | DateFormatter + SwiftFormat | PERFORMANCE | pending | CLEAN | DRAFT salvage |
| repoprompt-ce | 127 | dependabot | upload-artifact major | DEPENDENCY | GREEN | CLEAN | ESCALATE tip (0dw) |
| repoprompt-ce | 126 | dependabot | download-artifact major | DEPENDENCY | GREEN | CLEAN | ESCALATE tip (0dw) |

**In-scope open at Phase 2 start:** 7  
**Salvage drafts opened:** 1 (#133)  
**Closed superseded:** 1 (#132)  
**Escalated (left open):** 5  
**Ready for human merge (no draft):** 1 (#1036)  
**Autonomous merges:** 0
