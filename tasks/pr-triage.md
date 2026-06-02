# PR Triage — 2026-06-02

**Session:** Automated PR review (review-and-merge)  
**Preflight:** PASS

## Phase 1 dispositions (summary)

| Disposition | Count | Executed |
| --- | ---: | ---: |
| MERGE | 6 | 6 |
| CLOSE-DUPLICATE / superseded | 3 | 3 |
| ESCALATE | 4 | 4 (comments posted) |
| DEFER | 9 | 0 (queue retained) |

## Duplicate / overlap groups

### ZipSlip (email-security-pipeline)

| PR | Role | Action |
| --- | --- | --- |
| #1011 | Messy Sentinel branch (scratch files) | **CLOSED** → use #1008 |
| #1008 | Clean salvage of #999 | **ESCALATE** — human merge |
| #999 | Original (if still open) | Close when #1008 lands |

### Secure-permissions test duplicates

| PR | Role | Action |
| --- | --- | --- |
| #1009 | Canonical | **DEFER** until conflicts cleared |
| #1003 | Duplicate | **CLOSED** |

### Seatek `code_health_scanner.py`

| PR | Role | Action |
| --- | --- | --- |
| #241 | Fresher Bolt optimization | **MERGED** |
| #239 | Salvage of #237 | **CLOSED** superseded |

### personal-config scratch_* performance

| PR | Role | Action |
| --- | --- | --- |
| #1147 | Salvage #1117 (`scratch_triage`) | **MERGED** |
| #1150 | Bolt `scratch_inventory` | **ESCALATE** (toolchain trust boundary) |
| #1146 | Draft salvage #1142 | **DEFER** |
| #1145 | Draft salvage #1132 | **DEFER** |

## Conflict cascade (email-security-pipeline)

After merges on `main`, multiple Jules test PRs from 2026-06-01 show **CONFLICTING/DIRTY** (#996, #989, #984, #982, #972, #973). **Rule (Lesson 0):** run `gh api -X PUT repos/abhimehro/email-security-pipeline/pulls/<n>/update-branch` after #1008 lands, then re-triage; close zero-diff siblings.

## Ready-to-execute human actions

```bash
# 1. Merge security salvage (after human review of diff)
gh pr merge 1008 --repo abhimehro/email-security-pipeline --squash --delete-branch

# 2. Fix bandit failure on workflow PR or close until green
gh pr checks 1006 --repo abhimehro/email-security-pipeline

# 3. Review toolchain PR before merge
gh pr diff 1150 --repo abhimehro/personal-config

# 4. Refresh conflicted ESP test PRs after main moves
for n in 996 989 984 982 972 973; do
  gh api -X PUT "repos/abhimehro/email-security-pipeline/pulls/${n}/update-branch" || true
done

# 5. Mark draft salvages ready when reviewed
gh pr ready 1146 --repo abhimehro/personal-config
gh pr ready 1145 --repo abhimehro/personal-config
```

## Post-session remainder (YAML handoff)

```yaml
open_followups:
  - repo: abhimehro/personal-config
    pr: 1150
    reason: ESCALATE — scratch_inventory toolchain + CodeScene fail
  - repo: abhimehro/personal-config
    pr: 1146
    reason: DEFER — draft salvage #1142
  - repo: abhimehro/personal-config
    pr: 1145
    reason: DEFER — draft salvage #1132
  - repo: abhimehro/email-security-pipeline
    pr: 1008
    reason: ESCALATE — ZipSlip security salvage
  - repo: abhimehro/email-security-pipeline
    pr: 1006
    reason: ESCALATE — workflow SHA bumps; bandit failed
  - repo: abhimehro/email-security-pipeline
    pr: 973
    reason: ESCALATE — Sentinel NLP eval; DIRTY + large diff
```
