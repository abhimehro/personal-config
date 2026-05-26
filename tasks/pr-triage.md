# PR Triage — 2026-05-26

**Preflight:** PASS (6/6)  
**Disposition key:** MERGE · CLOSE-DUPLICATE · CLOSE-CONFLICT · DEFER · ESCALATE

## Duplicate / overlap groups

### Spam analyzer perf (email-security-pipeline)

| Keeper | Closed |
| --- | --- |
| **#936** (merged) | #935 — identical diff, older branch |

### ctrld-sync `_filter_rules_for_folder`

| Keeper | Closed |
| --- | --- |
| **#849** (merged, Bolt) | #847 — salvage duplicate + failing benchmark |

### Seatek Bolt perf cluster (#209–#214)

| Action | PRs |
| --- | --- |
| **CLOSED** | #209–#214 — all CONFLICTING with `main`; superseded by merged #226 and salvage #223/#224 |

## Phase 1 dispositions

| Disposition | Count | PRs |
| --- | ---: | --- |
| MERGE | 7 | pc #1064, #1066, #1071; cs #849; esp #936; Seatek #226; Hydro #206; sc #74 |
| CLOSE-DUPLICATE | 2 | esp #935; cs #847 |
| CLOSE-CONFLICT | 6 | esp #905; Seatek #209–#214 (5 closed; #209 last) |
| DEFER | 5 | pc #1065; esp #937, #933; sc #72, #73 |
| ESCALATE | 5 | pc #1070, #1068; esp #932; Seatek #223, #224 |

## Merge order executed

1. personal-config #1064 (docs — review session)
2. personal-config #1066 (docs — salvage session; conflict resolved after #1064)
3. personal-config #1071 (auth-hygiene allowlist)
4. ctrld-sync #849 (perf — local pytest 339 pass)
5. email-security-pipeline #936 (perf — local pytest 590 pass)
6. series_correction #74 (pandas agg)
7. Hydrograph #206 (dict zip perf)
8. Seatek_Analysis #226 (sensor parsing)

## Security gate notes

- **#1071:** Allowlist-only change to `verify-repo-auth-hygiene.sh`; no secrets added.
- **#936:** Spam detection logic change; substring pre-check preserves regex fallback path; tests green locally.
- **#932:** TOCTOU fix — escalated despite pytest/CodeQL green (security trust boundary).
- **#1070 / #1068:** Toolchain files — never auto-merge per policy.

## Human merge queue (priority)

1. **email-security-pipeline #932** — security TOCTOU (T1)
2. **personal-config #1070, #1068** — toolchain review
3. **Seatek #223, #224** — automation script boundary
4. **email-security-pipeline #933** — IMAP perf salvage
5. **series_correction #72, #73** — after CodeScene green
6. **personal-config #1065** — scratch_triage after CodeScene green
7. **email-security-pipeline #937** — after required CI infra fixed
