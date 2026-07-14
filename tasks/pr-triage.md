# PR Triage — 2026-07-14

## Duplicate & overlap groups

### personal-config — Sentinel eval removal (#1593 vs #1605)

- **Overlap:** Both modify `scripts/repair-controld-keepalive.sh` to remove `eval` in SUDO_USER resolution.
- **Keep:** #1605 (newer; adds `.github/gitleaks.toml`, `resolve_conflict.sh`, expanded `.jules/sentinel.md`).
- **Close:** #1593 — superseded.

### ctrld-sync — Palette leading-newline prompts (#1006 vs #1008)

- **Overlap:** Both fix terminal residue for interactive prompts with leading `\n` in `main.py`.
- **Keep:** #1008 (newer, focused diff; #1007 test updates align with #1008).
- **Close:** #1006 — superseded.

### Hydrograph — Pandas/numpy min-max (#344 / #354 / #355)

- **Overlap:** All touch `validator.py` and `chart_generator.py` for numpy min/max optimization.
- **Keep:** #355 (newest; green CodeScene; supersedes QA bugfix attempt in #354 and earlier Bolt #344).
- **Close:** #344, #354 — superseded.

## No-op QA PRs (0 file changes)

| PR | Repo | Action |
|----|------|--------|
| #1604 | personal-config | CLOSE |
| #1258 | email-security-pipeline | CLOSE |
| #451 | Seatek_Analysis | CLOSE |
| #223 | series_correction_project_updated | CLOSE |

## Draft / session-report superseded

| PR | Repo | Action | Reason |
|----|------|--------|--------|
| #1603 | personal-config | CLOSE | Draft evening salvage report; canonical artifacts from 2026-07-14 cron |

## Merge ordering applied

1. **Security fixes first:** pc #1605 (eval removal)
2. **Parallel a11y:** pc #1606, then pc #1602 (autofix palette.md conflict after #1606)
3. **ctrld-sync:** #1008 → #1007 → #1009
4. **Hydrograph:** #355 (after closing #344/#354)

## Escalation tail (Phase 2 salvage input)

| Repo | PR | Blocker |
|------|-----|---------|
| ctrld-sync | #990 | SSRF allowlist trust boundary + CodeScene FAIL (`/cs-agent` posted) |
| series_correction_project_updated | #210 | CLI exception sanitization — security-sensitive salvage of #205 |
| repoprompt-ce | #112 | Ephemeral URLSession / persisted token leak — networking trust boundary |
