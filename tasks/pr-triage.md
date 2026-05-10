# PR Triage — 2026-05-09 backlog cleanup (review-and-merge)

**Policy:** Squash merge, stale threshold 30 days (no qualifying **stale closures** this run — queue skews under 7 days old), auto-fix enabled (no branch pushes this pass; no safe auto-fix opportunities taken).

## SUPERSEDED

- abhimehro/Seatek_Analysis#162 — superseded by **#164** (CRITICAL OOM fix on same `Updated_Seatek_Analysis.R` path); closed after **#164** merged.

## DUPLICATE

- abhimehro/email-security-pipeline#786 — duplicate of **#785** (identical `caching.py` / test / journal delta); **#785** merged first, **#786** closed.

## STALE (>30d, no activity)

- _(none in-scope at snapshot; re-evaluate on next run with `updatedAt` vs `stale_threshold_days`.)_

## CONFLICTING / DEFER (human rebase; no force-push)

- abhimehro/series_correction_project_updated#13, #14 — conflicts after **#12** squash-merge (Lesson 0cc cascade).
- abhimehro/ctrld-sync#771 — conflicts after **#773** merge (same pluralization lane).
- abhimehro/Seatek_Analysis#163 — **UNSTABLE** CI at snapshot; not merged.

## READY (merged this session — cross-check `main`)

- abhimehro/dotfiles#907, #904
- abhimehro/email-security-pipeline#785
- abhimehro/series_correction_project_updated#12
- abhimehro/Seatek_Analysis#164, #161
- abhimehro/Hydrograph_Versus_Seatek_Sensors_Project#172
- abhimehro/ctrld-sync#773

## ESCALATE / trust boundary (commented; not merged)

- abhimehro/dotfiles#893 — `summary.yml` / LLM output → shell trust boundary (re-tagged in session comment).
- abhimehro/ctrld-sync#769 — Devin branch: shell injection hardening in automation summary path.
- abhimehro/ctrld-sync#775 — Sentinel authorization / log leakage class (overlaps **#772**, **#774**, **#770**; needs human dedup).

## ZERO-DIFF CLOSED (no merge; Lesson 0b)

- abhimehro/dotfiles#908
- abhimehro/email-security-pipeline#788, #782

## REMAINING HIGH-VOLUME (dotfiles repo)

Large overlapping Bolt/Jules/Sentinel queues (**#901** `CONFLICTING`, **#910**–**#903**, etc.): prefer **one semantic lane** at a time; re-fetch `mergeable` after each merge (Lesson 0cc).
