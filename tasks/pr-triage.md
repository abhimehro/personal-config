# PR Triage — 2026-07-31 Phase 2

## Disposition key

- **SALVAGE** — draft PR opened; original closed superseded
- **CLOSE-SUPERSEDED** — change already on main / twin
- **ESCALATE** — security / trust boundary / broken diff
- **DEFER** — large / CI-red / redesign
- **REQUEST_CHANGES** — junk or scope creep
- **AUTO-RESOLVED** — was CONFLICTING, now CLEAN (Phase 1 re-run)

## Decisions

| Repo | PR | Disposition | Why |
|------|----|-------------|-----|
| pc | 1840/1835 | SALVAGE → #1856 | a11y skip-link; journal append-only |
| pc | 1824/1823 | SALVAGE → #1857 | micro-opts combined (0ey) |
| pc | 1830 | CLOSE-SUPERSEDED | regex already #1854; harmful extras |
| pc | 1822/1841 | ESCALATE | CORS / auth env |
| pc | 1825 | REQUEST_CHANGES | scratch artifacts |
| pc | 1852 | DEFER | large maintenance |
| ctrld | 1086 | REQUEST_CHANGES | junk json |
| ctrld | 1088/1081 | DEFER | CodeScene / CI |
| esp | 1394 | DEFER | god-module (S6) |
| seatek | 552 | SALVAGE → #571 | T1 injection harden |
| seatek | 554 | DEFER | warn_on_* redesign |
| seatek | 560 | REQUEST_CHANGES | workflow scope |
| seatek | 568/555 | ESCALATE | path / workspace_roots |
| hg | 443/442 | AUTO-RESOLVED | CLEAN after #440 |
| hg | 445 | ESCALATE | path traversal |
| hg | 441 | DEFER | numpy runtime bump |
| series | 336 | ESCALATE | broken authenticate + CHANGELOG wipe |
| series | 322 | ESCALATE/DEFER | auth-adjacent multi-file |
| series | 337 | REQUEST_CHANGES | NaN masking |
| rpce | 147/158 | ESCALATE | workflows / TOCTOU |
| rpce | 144/159/161/157/152/148 | DEFER | CI/huge |
