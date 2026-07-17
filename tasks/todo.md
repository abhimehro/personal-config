# ABHI-1321 follow-ups (user feedback 2026-07-17)

- [x] Narrow gitleaks allowlist: removed broad `^tasks/`; added documented
      stopword `^scanning$` for `secret scanning` FP (personal-config-generic-secret)
- [x] Re-enable Jules workflow (was `disabled_manually` → `active`); schedule intact
- [x] Keep Gemini deleted (confirmed; README updated)
- [x] PR #1670 already ready-for-review; macOS audit jobs green
- [x] Dispatch Jules smoke retest; update Linear
  - Dispatch run: https://github.com/abhimehro/personal-config/actions/runs/29608663848 (success, 6/6 matrix)
  - Sample issue: https://github.com/abhimehro/personal-config/issues/1683
  - Watch whether Jules bot comments on those issues (known gap to retest)
