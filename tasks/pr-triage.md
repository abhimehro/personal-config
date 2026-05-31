# PR Triage — 2026-05-31

**Preflight:** PASS (6/6)  
**Disposition key:** MERGE · DEFER · CLOSE-SUPERSEDED · ESCALATE · CLOSE-DUPLICATE

## Duplicate / overlap groups

| Group | Keeper | Action on others |
| --- | --- | --- |
| Session doc artifacts (personal-config) | **This session PR** (`cursor-agent/automated-pr-salvage-workflow-4f93`) | After merge: close #1096 as superseded by #1102; close #1102 when #4f93 lands |
| Jules Daily QA (ESP) | **#968** (formatting, all green) | None — #970 is Palette UX, different intent |

## Dispositions

| Disposition | PRs | Executed action (this session) |
| --- | --- | --- |
| **MERGE** | pc #1093; esp #968; ctrld #861 | `gh pr merge --squash` (see session report) |
| **DEFER** | esp #966; esp #970 (if Bugbot blocks) | Comment + Phase 2 queue |
| **ESCALATE** | pc #1103 | Human review (launchd + secops scripts) |
| **CLOSE-SUPERSEDED** | pc #1096 | After artifact PR #4f93 merges |

## Security review notes

| PR | Tier | Assessment |
| --- | --- | --- |
| ctrld #861 | T4 Palette UX | User-facing log string only; no auth/secrets. Benchmark alert is CI baseline noise (Lesson 0dr). |
| esp #968 | T5 chore | Black/formatting only; bandit + pytest green. |
| esp #966 | CI/INFRA | Proposed `codeql-bundle-v2.25.5` tag violates org SHA-only policy — defer, do not merge. |
| esp #970 | T4 Palette UX | Menu copy/layout; pytest green; merge after advisory checks settle. |
| pc #1103 | T2 trust boundary | New launchd agents + `ai_engine.sh` — human approval required despite green CI. |
| pc #1093 | T5 docs | `.jules/bolt.md` guidance only — safe to merge. |

## CI anomalies

| PR | Check | Root cause |
| --- | --- | --- |
| ctrld #861 | benchmark | github-action-benchmark regression vs prior commit on branch; unrelated to 4-line log change (Lesson 0dr) |
| esp #966 | bandit | Workflow pin PR uses `upload-sarif@codeql-bundle-v2.25.5` — org requires full commit SHA |
| esp #970 | Cursor Bugbot | IN_PROGRESS / NEUTRAL — non-blocking for application checks |
| ctrld main | benchmark | Pre-existing failures on `main` (3 recent runs failed) — infra lane, not PR-specific |

## Ready-to-execute human actions

```bash
# After green CI on draft #1005 (from memory) — human only
# gh pr merge 1005 --repo abhimehro/personal-config --squash

# Secops feature — review launchd PATH and ai_engine.sh before merge
# gh pr view 1103 --repo abhimehro/personal-config

# ESP workflow automation — fix bandit.yml SARIF pin to full SHA, then re-run #966
# gh pr checks 966 --repo abhimehro/email-security-pipeline
```
