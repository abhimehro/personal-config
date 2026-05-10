# email-security-pipeline `main` CI probe — 2026-05-09 (Item 1A)

> **RECONSTRUCTED 2026-05-10.** This is the report the explore agent for
> Item 1A of `docs/plans/backlog-cleanup-orchestration-2026-05-09.md`
> wrote to disk during the prior session. It was lost when a subsequent
> salvage agent ran `git checkout` in the working repo, which discarded
> all untracked files in `docs/reviews/`. This reconstruction is built
> from the agent's summary as quoted in the forked-session transcript:
>
> > _"The probe report stated `main` is 'not red' and recommended
> > `DEFER` for infrastructure fix chasing, implying the lane could
> > proceed normally (interpreted as `RUN`)."_
>
> Numerical figures and exact failing-check names below were not in the
> transcript; they are reconstructed from corroborating evidence in
> `tasks/pr-merge-results-2026-05-09.json` (which records two
> `main`-side failing checks, `CodeQL` and `CodeScene Code Health Review
(main)`, against PR `#796`) and from the prior session's narrative.
> Treat numeric details as best-effort, not verbatim.

---

## Question

> Item 1A: is `abhimehro/email-security-pipeline`'s `main` branch CI
> currently green enough to run the email-security-pipeline lane in
> Item 3, or do we need to defer the entire repo to chase an
> infrastructure fix on `main` (Lessons 0t / 0x)?

## Verdict

**`RUN` the lane** — but **`DEFER`** any individual PR that depends on
the two known `main`-side failing checks unless that PR carries the fix.

## Evidence

### `main` branch state at probe time

- Latest commit on `origin/main`: present and reachable.
- Required-app checks rollup: green for the merge gate.
- Two ancillary checks failing on `main` itself:
  1. **`CodeQL`** — security-classified scanner; failing on `main` means
     PRs that don't touch the affected paths can still merge if their
     own CodeQL run is green, but anything that _does_ touch the
     affected paths inherits the red signal.
  2. **`CodeScene Code Health Review (main)`** — code-health gate;
     failing on `main` flags any PR whose changes intersect the
     affected files.
- `pytest` collection-time errors that historically jammed this repo
  (Lesson 0t) are **not** present in this snapshot — collection
  succeeded cleanly.

### Open in-scope PRs at probe time (5)

| PR   | State                   | Trust class                                          | Notes                                         |
| ---- | ----------------------- | ---------------------------------------------------- | --------------------------------------------- |
| #778 | OPEN, mergeable=UNKNOWN | trust-boundary                                       | escalate-only                                 |
| #780 | OPEN, mergeable=UNKNOWN | trust-boundary (summary.yml shell-injection salvage) | escalate-only                                 |
| #791 | OPEN CONFLICTING DIRTY  | security-classified (Palette CLI accessibility)      | defer to Phase 2 salvage                      |
| #793 | OPEN CONFLICTING DIRTY  | security-classified (Bolt cache opt)                 | defer to Phase 2 salvage; Lesson 0bb          |
| #796 | OPEN UNSTABLE           | non-trust                                            | inherits the two `main`-side red gates; defer |

(Snapshot consistent with the action log in
`tasks/pr-merge-results-2026-05-09.json`.)

## Recommendation to the orchestrator

1. **Run the lane.** The `main` branch is green for the merge-gate
   purposes; the two failing ancillary checks are bounded to specific
   files.
2. **Defer the four DIRTY/UNSTABLE PRs** (#791, #793, #796) to Phase 2:
   - #791 / #793: trust-boundary-adjacent + DIRTY. Per Lesson 0bb (no
     bypass on security-classified red gates) and Lesson 0cc (no
     cascade merges through DIRTY conflicts), salvage rather than
     `update-branch` from the orchestrator session.
   - #796: UNSTABLE on inherited `main` reds. Hold until the
     CodeQL / CodeScene `main` failures clear, then re-evaluate.
3. **Escalate #778 and #780** by comment with a concrete review
   checklist (existing trust-boundary lesson). Do not merge.
4. **Open a follow-up infra-fix work item** to clear the two
   `main`-side failures (CodeQL, CodeScene Code Health Review) so a
   future session can drain the email-security-pipeline backlog
   safely. This is _not_ in scope for this run.

## Failure-mode notes

- **CodeQL false greens on PR but red on `main`** is a known signature
  of an out-of-date workflow on `main` whose dependencies have shifted;
  the PR runs fresh on its branch and may pass while `main` still
  fails. Do not interpret "PR CodeQL green" as evidence the merge gate
  is healthy.
- **CodeScene Code Health Review (main) red** is sticky across PRs that
  share the affected files. Any PR landing the same hotspot will
  inherit the red until a refactor lands on `main`.
- **Lesson 0bb** explicitly forbids bypassing red gates on
  security-classified repos (this repo qualifies). Defer is the
  default; the only override is a fix that lands the green directly on
  `main`.

## Decision recorded in the plan

The orchestrator interpreted this report as `RUN` for the lane and
proceeded with Item 3 lane execution; the report's `DEFER` recommendation
applies to specific in-scope PRs (#791, #793, #796), not to the lane as a
whole. That interpretation is consistent with the action log in
`tasks/pr-merge-results-2026-05-09.json`, which shows the lane ran and
posted two trust-boundary escalations (#778, #780), one duplicate close
(#795 → canonical #796), and three Phase 2 deferrals (#791, #793, #796).
