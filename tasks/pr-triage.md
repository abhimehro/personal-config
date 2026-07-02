# PR Triage — 2026-07-02

**Session:** Automated PR review (cron 13:00 UTC)  
**Mode:** review-and-merge

## Duplicate & overlap analysis

### series_correction_project_updated #166 vs #169

- **Overlap:** Both touch `scripts/processor.py` + `.jules/bolt.md` with same Bolt intent (jump-window extraction).
- **Decision:** Keep #169 (CLEAN, passing CI). Close #166 (CodeScene failure, older branch).
- **Action:** Closed #166 with link to #169.

### personal-config #1448 vs #1455

- **Overlap:** Both consolidate `maintenance/bin/service_monitor.sh` ps-aux polling into single awk pass.
- **Decision:** Keep #1455 (ready, non-draft Bolt branch). Close #1448 (draft salvage of #1446).
- **Action:** Closed #1448 with link to #1455.

### email-security-pipeline #1207 vs #1202

- **Overlap:** Both touch `src/modules/alert_system.py` but different regions (#1207 keyword patterns ~L66; #1202 URL redaction ~L645).
- **Decision:** Merge #1207 first (security-adjacent perf). #1202 went DIRTY after #1207 merge — defer per Lesson 0 cascade.
- **Action:** Merged #1207; deferred #1202 for rebase/salvage.

### Seatek_Analysis #393

- **Type:** Zero-diff Daily QA (`changedFiles: 0`).
- **Decision:** Close — no effective changes vs `main`.
- **Action:** Closed #393.

### personal-config #1452

- **Type:** Session-doc draft from prior cursor-agent salvage run.
- **Decision:** Close — superseded by this session's consolidated report on `cursor-agent/automated-pr-workflow-2874`.
- **Action:** Closed #1452.

## Stale check (30-day threshold)

No in-scope PR exceeded 30 days. Oldest open at start was ctrld #965 and esp #1190 (~1 day).

## Security gate results

| PR | Gate | Notes |
|----|------|-------|
| esp #1206 | PASS | URL parsing hardening; no secrets, minimal scope |
| ctrld #969 | PASS | Sentinel security improvement; 4-line addition |
| hg #312 | PASS | Removes ineffective test assertions (security theater) |
| esp #1207 | PASS | Regex perf only; pre-compiled patterns |
| pc #1455 | PASS | Shell perf; no privilege escalation |
| rpce #82 | PASS | Static DateFormatter extraction; no Keychain changes |

No security gate failures this session.

## CI infra observations

- **CodeScene:** ctrld #965 and sc #168 fail CodeScene Code Health — posted `/cs-agent skill:fix-code-health-degradations` on both.
- **Merge cascade:** esp #1202 conflict after #1207 is expected hot-file cascade (Lesson 0), not infra breakage on `main`.
- **Daily QA:** esp #1190 remains DIRTY umbrella PR — escalate to human (28 files, not zero-diff).

## Merge ordering applied

1. Security: esp #1206 → ctrld #969 → hg #312  
2. Perf: esp #1207 → esp #1203 → esp #1202 (failed — cascade)  
3. Tests/salvage: esp #1204 → pc #1450/#1451/#1449  
4. Perf/docs: pc #1455 → pc #1456 → sc #169 → rpce #82  

## Repos at zero open in-scope PRs (post-session)

- personal-config
- Seatek_Analysis
- Hydrograph_Versus_Seatek_Sensors_Project
- repoprompt-ce
