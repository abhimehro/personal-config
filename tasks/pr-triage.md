# PR Triage — 2026-07-19 — FINAL

## Duplicate / overlap

| Group | Keep | Close | Outcome |
|-------|------|-------|---------|
| ctrld-sync style + countdown | #1028 | #1027 | Merged #1028; closed #1027 |
| Zero-diff Daily QA | — | Seatek #489, sc #249 | Closed |
| Phase 2 salvage docs | this session | #1686 | Closed; lessons folded |

## Autofixes applied

1. **pc #1694:** deleted incomplete `patch_all_vulns.py`
2. **esp #1299 cycle 1:** restored kebab-case `greetings.yml` (Lesson 0dz)
3. **esp #1299 cycle 2:** resolved `setup_wizard.py` formatting conflict after #1300

## Escalations (Phase 2 input)

```yaml
- repo: abhimehro/personal-config
  pr: 1670
  reason: CONFLICTING Gemini/gitleaks/shellcheck trust boundary (Lesson 0ea)
- repo: abhimehro/Hydrograph_Versus_Seatek_Sensors_Project
  pr: 374
  reason: numpy 1.26→2.2 major
- repo: abhimehro/series_correction_project_updated
  pr: 233
  reason: auth logic hard gate
- repo: abhimehro/repoprompt-ce
  pr: 126
  reason: download-artifact major on main-tip (Lesson 0dw)
- repo: abhimehro/repoprompt-ce
  pr: 127
  reason: upload-artifact major on main-tip (Lesson 0dw)
```
