# PR Triage and Disposition - 2026-05-02

Source inventory: `tasks/pr-inventory.md` from Work Item 1. This file is read-only triage only: no PRs were merged, closed, fixed, pushed, or commented on during Work Item 2.

## Decision Rules Applied

- Security-sensitive canonical PRs are `ESCALATE`, including path traversal, SSRF/IP validation, option/command/terminal injection, security alert rendering, media parsing of untrusted attachments, and macOS security audit logic.
- Zero-diff PRs are `CLOSE-ZERO-DIFF`.
- Redundant sibling PRs are `CLOSE-SUPERSEDED` and explicitly point to the canonical PR, even when that canonical PR is itself escalated.
- Failing or pending CI does not create `MERGE-AFTER-FIX` unless the issue is a documented safe routine auto-fix. None of the 42 PRs met that bar.
- No PR is stale: the inventory maximum age is 4 days, below the 30-day stale threshold.

## Hydrograph_Versus_Seatek_Sensors_Project

|  PR | Disposition      | Canonical PR | Rationale                                                                                                                             |
| --: | ---------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| 158 | CLOSE-SUPERSEDED | #155         | Same `validator.py` `isna().sum()` optimization family; fails one check and is covered by the clean focused canonical optimization.   |
| 157 | ESCALATE         | #157         | Sentinel path traversal fix in `utils/utils.py`; security-sensitive file path validation requires human review.                       |
| 155 | MERGE            | #155         | Focused performance optimization in `src/hydrograph_seatek_analysis/data/validator.py`; CI clean and no security boundary identified. |
| 153 | CLOSE-SUPERSEDED | #155         | Same `validator.py` optimization family; failing CI and redundant with #155.                                                          |
| 152 | CLOSE-SUPERSEDED | #155         | Same `validator.py` optimization family; pending/unstable check state and redundant with #155.                                        |
| 150 | CLOSE-SUPERSEDED | #155         | Same `validator.py` optimization family plus benchmark artifact; failing CI and redundant with #155.                                  |

## Seatek_Analysis

|  PR | Disposition | Canonical PR | Rationale                                                                                                                                             |
| --: | ----------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| 158 | MERGE       | #158         | Dependabot pandas requirement update under `Series_27/Analysis`; CI clean, single requirements file, no auth/payment/DB/security boundary identified. |

## ctrld-sync

|  PR | Disposition      | Canonical PR | Rationale                                                                                                                            |
| --: | ---------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| 754 | ESCALATE         | #754         | Canonical SSRF/reserved-IP protection change in `main.py`; security-sensitive network validation.                                    |
| 753 | CLOSE-ZERO-DIFF  | n/a          | Zero changed files.                                                                                                                  |
| 752 | CLOSE-SUPERSEDED | #754         | Same SSRF/reserved-IP fix family; covered by canonical #754.                                                                         |
| 751 | ESCALATE         | #751         | Canonical fail-secure interactive prompt change in live sync flow; affects safety behavior and includes dependency/lockfile changes. |
| 750 | CLOSE-ZERO-DIFF  | n/a          | Zero changed files.                                                                                                                  |
| 749 | CLOSE-SUPERSEDED | #754         | Same SSRF/reserved-IP fix family; covered by canonical #754.                                                                         |
| 748 | CLOSE-SUPERSEDED | #751         | Same fail-secure prompt family; covered by canonical #751.                                                                           |
| 747 | CLOSE-SUPERSEDED | #751         | Same fail-secure prompt family; covered by canonical #751.                                                                           |
| 746 | CLOSE-SUPERSEDED | #754         | Same SSRF/reserved-IP fix family; covered by canonical #754.                                                                         |
| 745 | CLOSE-SUPERSEDED | #754         | Same SSRF/reserved-IP fix family; covered by canonical #754.                                                                         |

## email-security-pipeline

|  PR | Disposition      | Canonical PR | Rationale                                                                                                                                             |
| --: | ---------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| 749 | MERGE            | #749         | Focused test-only `mock_os_open` assertion cleanup in `tests/test_setup_wizard.py`; CI clean and no product behavior change.                          |
| 748 | CLOSE-SUPERSEDED | #732         | Video frame extraction optimization is covered by #732; this sibling is unstable/failing.                                                             |
| 747 | ESCALATE         | #747         | Canonical suspicious URL CLI alert rendering change; security-sensitive threat visibility in email pipeline and currently unstable/failing.           |
| 746 | CLOSE-SUPERSEDED | #747         | Same suspicious URL alert rendering family, with extra setup/app-runner churn; superseded by canonical #747.                                          |
| 743 | CLOSE-SUPERSEDED | #749         | Same setup-wizard test assertion family but also comments out ML dependencies in `requirements.txt`; superseded by the focused canonical #749.        |
| 742 | CLOSE-SUPERSEDED | #749         | Same setup-wizard test assertion family; superseded by canonical #749.                                                                                |
| 740 | CLOSE-SUPERSEDED | #732         | Same video frame extraction optimization as #748/#732; unstable/failing and superseded by canonical #732.                                             |
| 738 | CLOSE-SUPERSEDED | #749         | Same setup-wizard test fix family but also changes `requirements.txt`; superseded by focused canonical #749.                                          |
| 736 | CLOSE-SUPERSEDED | #749         | Same setup-wizard test fix family with requirements churn; superseded by focused canonical #749.                                                      |
| 733 | CLOSE-SUPERSEDED | #749         | Same focused `mock_os_open` assertion cleanup; superseded by newer canonical #749.                                                                    |
| 732 | ESCALATE         | #732         | Canonical video frame extraction optimization in `media_analyzer.py`; untrusted media parsing boundary requires human review even though CI is clean. |
| 731 | CLOSE-SUPERSEDED | #732         | Same video frame extraction optimization family; superseded by canonical #732.                                                                        |

## personal-config

|  PR | Disposition      | Canonical PR | Rationale                                                                                                                                           |
| --: | ---------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| 850 | ESCALATE         | #850         | Option-injection hardening for `pgrep`/`pkill` in macOS/system automation scripts; security-sensitive system command logic.                         |
| 849 | ESCALATE         | #849         | Canonical forgiving prompt/UI change also rewrites `mac-audit` security audit conditionals and cleanup/setup prompts; security/tooling boundary.    |
| 840 | ESCALATE         | #840         | Canonical QA/refactor in `mac-audit` security audit logic; security-sensitive audit behavior.                                                       |
| 839 | ESCALATE         | #839         | Performance change includes `mac-audit` security audit conditionals plus AdGuard list scripts; security-adjacent audit behavior needs human review. |
| 838 | ESCALATE         | #838         | Command injection fix via `eval`; conflicting, failing, and touches a large unclear trust boundary.                                                 |
| 837 | CLOSE-SUPERSEDED | #849         | Same forgiving cleanup prompt family as #849, but conflicting and too large to diff via GitHub; superseded by canonical #849.                       |
| 836 | ESCALATE         | #836         | Password redaction/security-sensitive content plus 870-file conflicting diff; unclear trust boundary.                                               |
| 835 | CLOSE-SUPERSEDED | #849         | Same interactive yes/no prompt UX family; conflicting huge diff superseded by canonical #849.                                                       |
| 834 | CLOSE-SUPERSEDED | #840         | Same Daily QA / agentic review family; conflicting huge diff superseded by canonical #840.                                                          |
| 833 | CLOSE-SUPERSEDED | #840         | Same Daily QA / agentic review family; conflicting huge diff superseded by canonical #840.                                                          |
| 832 | ESCALATE         | #832         | Terminal injection fix for Control D manager; security-sensitive system/network automation and conflicting huge diff.                               |
| 831 | ESCALATE         | #831         | Graceful-exit change is conflicting with an 866-file diff touching agent/tooling paths; unclear trust boundary and no clean canonical PR.           |
| 830 | CLOSE-SUPERSEDED | #840         | Same Daily QA / agentic review family; conflicting huge diff superseded by canonical #840.                                                          |

## Disposition Counts

| Disposition      |  Count |
| ---------------- | -----: |
| MERGE            |      3 |
| MERGE-AFTER-FIX  |      0 |
| CLOSE-DUPLICATE  |      0 |
| CLOSE-SUPERSEDED |     24 |
| CLOSE-STALE      |      0 |
| CLOSE-ZERO-DIFF  |      2 |
| DEFER            |      0 |
| ESCALATE         |     13 |
| **Total**        | **42** |

## Uncertain / Human-Review Cases

- `personal-config` #830-#838 remain the highest-uncertainty group: GitHub reports 866-870 changed files, `CONFLICTING/DIRTY`, and `gh pr diff` refuses full diffs with `PullRequest.diff too_large`. Redundant prompt/QA siblings are mapped to clean canonical PRs; security-sensitive or non-redundant siblings are escalated.
- `personal-config` #849/#840/#839 are CI-clean but touch `mac-audit` security audit logic, so they are escalated under the strict security-sensitive rule instead of marked merge-ready.
- `email-security-pipeline` #732/#747 touch security-relevant analysis/alerting paths for untrusted email/media content and should not be autonomously merged.
- `Seatek_Analysis` #158 is a major pandas-range update, but it is single-file, Dependabot-authored, CI-clean, and outside the documented escalation boundaries.

## Execution Results - Work Item 3 (2026-05-02)

Closures were executed first. Merge candidates were re-checked immediately before squash merge for `OPEN`, non-draft, `MERGEABLE/CLEAN`, and green/skipped checks; remaining merge candidates were re-checked after each merge.

| Result                   | Count |
| ------------------------ | ----: |
| Merged                   |     3 |
| Closed                   |    26 |
| Skipped                  |     0 |
| Newly escalated/deferred |     0 |

### Merged

| Repo                                                 |  PR | Result                              |
| ---------------------------------------------------- | --: | ----------------------------------- |
| `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project` | 155 | Squash-merged; post-state `MERGED`. |
| `abhimehro/Seatek_Analysis`                          | 158 | Squash-merged; post-state `MERGED`. |
| `abhimehro/email-security-pipeline`                  | 749 | Squash-merged; post-state `MERGED`. |

### Closed

| Repo                                                 |  PR | Result                        |
| ---------------------------------------------------- | --: | ----------------------------- |
| `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project` | 158 | Closed as superseded by #155. |
| `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project` | 153 | Closed as superseded by #155. |
| `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project` | 152 | Closed as superseded by #155. |
| `abhimehro/Hydrograph_Versus_Seatek_Sensors_Project` | 150 | Closed as superseded by #155. |
| `abhimehro/ctrld-sync`                               | 753 | Closed as zero-diff.          |
| `abhimehro/ctrld-sync`                               | 752 | Closed as superseded by #754. |
| `abhimehro/ctrld-sync`                               | 750 | Closed as zero-diff.          |
| `abhimehro/ctrld-sync`                               | 749 | Closed as superseded by #754. |
| `abhimehro/ctrld-sync`                               | 748 | Closed as superseded by #751. |
| `abhimehro/ctrld-sync`                               | 747 | Closed as superseded by #751. |
| `abhimehro/ctrld-sync`                               | 746 | Closed as superseded by #754. |
| `abhimehro/ctrld-sync`                               | 745 | Closed as superseded by #754. |
| `abhimehro/email-security-pipeline`                  | 748 | Closed as superseded by #732. |
| `abhimehro/email-security-pipeline`                  | 746 | Closed as superseded by #747. |
| `abhimehro/email-security-pipeline`                  | 743 | Closed as superseded by #749. |
| `abhimehro/email-security-pipeline`                  | 742 | Closed as superseded by #749. |
| `abhimehro/email-security-pipeline`                  | 740 | Closed as superseded by #732. |
| `abhimehro/email-security-pipeline`                  | 738 | Closed as superseded by #749. |
| `abhimehro/email-security-pipeline`                  | 736 | Closed as superseded by #749. |
| `abhimehro/email-security-pipeline`                  | 733 | Closed as superseded by #749. |
| `abhimehro/email-security-pipeline`                  | 731 | Closed as superseded by #732. |
| `abhimehro/personal-config`                          | 837 | Closed as superseded by #849. |
| `abhimehro/personal-config`                          | 835 | Closed as superseded by #849. |
| `abhimehro/personal-config`                          | 834 | Closed as superseded by #840. |
| `abhimehro/personal-config`                          | 833 | Closed as superseded by #840. |
| `abhimehro/personal-config`                          | 830 | Closed as superseded by #840. |

### Skipped / Newly Escalated or Deferred

None.
