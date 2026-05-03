# PR triage — backlog cleanup test (2026-05-03)

**Policy:** squash merge, stale_days 30, auto-fix enabled, mode review-and-merge. **No force-push.**

## Duplicate / supersede groups

| Keep (canonical)                 | Close as duplicate / superseded | Rationale                                                                                                            |
| -------------------------------- | ------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| personal-config **#854**         | **#850**, **#857**              | Same CWE-88 pgrep/pkill theme; **#854** CLEAN mergeable on latest snapshot; **#850/#857** CONFLICTING older branches |
| ctrld-sync **#761**              | **#759**, **#760**              | Identical title “Add ctrld-sync CLI testing skill”; keep newest PR                                                   |
| ctrld-sync **#755**              | **#754**                        | Both SSRF/reserved IP hardening; **#755** newer HIGH finding + broader test file set vs **#754** MEDIUM              |
| email-security-pipeline **#759** | **#752**, **#753**              | Same `spam_analyzer.py` Bolt URL caching; filenames overlap                                                          |
| email-security-pipeline **#758** | **#757**                        | Same sentinel TLS refactor branch family (`explicit-tls-verification`)                                               |

## Zero-diff / QA noise (close, do not squash-merge)

| PR                               | Action                                                 |
| -------------------------------- | ------------------------------------------------------ |
| personal-config **#873**         | CLOSE-STALE semantics → close as zero-diff (Lesson 0b) |
| personal-config **#871**         | CLOSE zero-diff                                        |
| email-security-pipeline **#755** | CLOSE zero-diff QA                                     |

## Escalate / defer (no autonomous merge)

| PR                                                     | Reason                                                                                                                      |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| personal-config **#838**, **#836**, **#832**, **#831** | CONFLICTING + very large diffs (~869 files); trust boundary / conflict resolution needs human                               |
| email-security-pipeline **#744**                       | CONFLICTING CI/requirements — potential migration/supply-chain scope                                                        |
| personal-config **#867** + **#884**                    | Both touch orchestration (`run_merges.py`); merge sequentially with re-check — **not** duplicates but **coordination risk** |

## UNSTABLE (investigate before merge)

| PR                                           | Gate                                                                |
| -------------------------------------------- | ------------------------------------------------------------------- |
| personal-config **#874**, **#858**, **#856** | Request `gh pr checks`; merge only if failures unrelated per policy |
| email-security-pipeline **#760**, **#747**   | Same                                                                |

## Recommended merge order (global)

1. **SECURITY / path fixes:** Hydrograph **#157**, email **#758**, email **#751**, ctrld **#755**, personal-config **#854**, then remaining personal-config Sentinel/eval fixes (**#876**, **#866**, **#864**, **#863**, **#881**) before broad Bolt perf merges.
2. **CI hygiene (low risk):** Devin changelog token PRs ctrld **#756**, email **#761**, Hydrograph **#161**; skills **#762**, ctrld **#757**, Hydrograph **#162**, personal-config Devin docs PRs.
3. **PERFORMANCE / REFACTOR:** Remaining CLEAN personal-config Bolt/Jules rows after each merge re-validation.

After **each** merge: refresh `gh pr list --json mergeable,mergeStateStatus` for siblings (Lesson 0).

## Stale (>30d inactive)

Snapshot: **none** met strict “last push + fail” stale closure policy; oldest mergeable heads still active May 2026.

---

## Outcomes (2026-05-03 execution)

- **Executed:** zero-diff closures (**personal-config** `#873` `#871`, **email-security-pipeline** `#755`); duplicate closures (**personal-config** `#850` `#857`, **ctrld-sync** `#754`, **email** `#752` `#753` `#757`); squash merges per [`tasks/pr-review-session-reports.md`](pr-review-session-reports.md) Run — 2026-05-03 (**36** total).
- **Deferred:** conflict tail (**personal-config** `#840` `#849` `#851` `#862` `#880` `#884`, **`#863`** earlier), Bolt overlap **`#867`** **`#869`**, mega conflicting **`#838`** **`#836`** **`#832`** **`#831`**, CI-red rollup (**personal-config** `#874` `#858` `#856`; **email** `#760` `#747`), requirements **`email#744`**, **`email#732`**.
