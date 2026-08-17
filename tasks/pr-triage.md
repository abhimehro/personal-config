# PR Triage — 2026-08-17 (Phase 1)

## Decision summary

### Merge now (done)

- ctrld [#1190](https://github.com/abhimehro/ctrld-sync/pull/1190) skill Docker/mypy docs
- ctrld [#1192](https://github.com/abhimehro/ctrld-sync/pull/1192) skill harness tips (after #1190 + update-branch)
- ctrld [#1185](https://github.com/abhimehro/ctrld-sync/pull/1185) test typing/side_effects
- esp [#1490](https://github.com/abhimehro/email-security-pipeline/pull/1490) unused DATABASE_* stubs
- esp [#1492](https://github.com/abhimehro/email-security-pipeline/pull/1492) Palette semantic colors
- rpce [#260](https://github.com/abhimehro/repoprompt-ce/pull/260) accessibilityLabel on two buttons

### Closed

- series [#400](https://github.com/abhimehro/series_correction_project_updated/pull/400) zero-diff Daily QA (0fr)
- ctrld [#1191](https://github.com/abhimehro/ctrld-sync/pull/1191) zero-diff
- ctrld [#1189](https://github.com/abhimehro/ctrld-sync/pull/1189) `display//` blueprint typo
- seatek [#681](https://github.com/abhimehro/Seatek_Analysis/pull/681) near-dup of #686

### REQUEST_CHANGES / HOLD (new this run)

- pc [#2014](https://github.com/abhimehro/personal-config/pull/2014) — `role="status"` on `<li>` overrides listitem (lesson **0ft**)
- seatek [#679](https://github.com/abhimehro/Seatek_Analysis/pull/679) / [#685](https://github.com/abhimehro/Seatek_Analysis/pull/685) — redundant argparse no-args path
- seatek [#686](https://github.com/abhimehro/Seatek_Analysis/pull/686) — `mean.default` without numeric contract
- rpce [#261](https://github.com/abhimehro/repoprompt-ce/pull/261) — static ISO8601DateFormatter not actor-isolated
- ctrld [#1170](https://github.com/abhimehro/ctrld-sync/pull/1170) — floating `gh-aw` tag (reaffirmed)

### Clusters (ESCALATE, Phase 2 drafts only)

- **CORS / CWE / SSRF (pc):** #1907, #2007, #2000, #1989, #1998, #1980
- **Path traversal (hg):** #528/#526/#524/#520 + salvage #507
- **TOCTOU (rpce):** #258/#254/#250/#243/#239
- **File-read DoS / yaml (seatek):** #680/#676/#667/#665/#662/#657
- **Majors with red CI:** seatek #661 numpy 1.26→2.5, series #393 numpy / #386 pandas 3, esp #1444 opencv 5, ctrld #1136 mypy 2.x
- **CI/toolchain:** seatek #684 workflow consolidate, esp #1473 requirements-ci default, ctrld #1187 settings validation
- **Salvage drafts:** rpce #244/#237, hg #507 — never merge in Phase 1
- **DIRTY:** ctrld #1188 uv-only, esp #1487 Bolt headers, pc join/HTML twins

### Human OOS

- pc [#1969](https://github.com/abhimehro/personal-config/pull/1969) skill-index workflow (Gitleaks + CodeScene)

### Duplicate / overlap notes

- seatek #679 ≡ #685 (CLI empty-state). Neither merged (argparse already handles no-args).
- seatek #681 ≈ #686 (`mean.default`). Closed #681; HOLD #686.
- rpce DateFormatter family (#261/#249/#241/#236) — HOLD concurrency; prefer function-local hoist.
- Palette a11y rpce #247/#253 still HOLD (junk `patch_formatter.py` / UNSTABLE).
