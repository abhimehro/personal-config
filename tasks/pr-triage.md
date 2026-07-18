# PR Triage — 2026-07-18 (FINAL)

## Duplicate / overlap

- None exact. Mid-session: Jules Daily QA #1297 appeared as ad-hoc root script — closed (not a duplicate of a fix PR; quality reject).

## Stale (>30d)

None.

## Cascade after merges

- **pc#1670** flipped `MERGEABLE` → `CONFLICTING` after #1679 (CI cache salvage) landed overlapping `.github/workflows/*` / actions. Remains ESCALATE; Phase 2 must rebase or close if superseded by cache work.

## Dispositions executed

### MERGED (9)

1. esp#1267 — GG cleared test refactor
2. hg#383 — colorlog 6.10.1→6.11.0
3. pc#1678 — docs archive salvage
4. pc#1681 — Palette HTML
5. cs#1023 — Palette emoji + safer ANSI strip
6. sc#247 — Bolt np.median optimization
7. pc#1679 — ShellCheck/Trunk CI cache salvage
8. pc#1677 — allowlist tests (Analyze swift flake ignored)
9. esp#1296 — first-interaction@v3 + kebab-case autofix

### CLOSED (1)

- esp#1297 — ad-hoc Jules Daily QA repro script (not mergeable)

### ESCALATE (5, carried)

| PR | Reason |
|----|--------|
| pc#1670 | Gemini/gitleaks workflow consolidation — CI trust boundary; now CONFLICTING vs #1679 |
| hg#374 | numpy 1.x→2.x major |
| sc#233 | Auth/password hashing |
| rpce#126 | download-artifact major 4→8 |
| rpce#127 | upload-artifact major 4→7 |
