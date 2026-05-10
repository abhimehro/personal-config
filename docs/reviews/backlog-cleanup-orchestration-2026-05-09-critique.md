# Critique — backlog cleanup orchestration plan (2026-05-09)

> **RECONSTRUCTED 2026-05-10.** The original Oracle critique document was
> written to `docs/reviews/` during the prior session and lost when a
> salvage agent's `git checkout` clobbered the untracked `docs/` subtree.
> Only the _outcome_ of the critique survives in the forked-session
> transcript ("polish pass tightened Background, added cluster-grouping,
> folded Open Questions into Item 1"). The critique items below are
> reverse-engineered from the diff between the pre-polish and post-polish
> plan, plus the prior agent's polish-pass narration. Mark this as
> _reconstructed-by-inference_ — useful for pattern review, not as a
> verbatim Oracle transcript.

---

## What the critique was for

After the orchestrator drafted the first version of
`docs/plans/backlog-cleanup-orchestration-2026-05-09.md`, it asked the
Oracle (via `ask_oracle mode:"review"`) to surface gaps, redundancies, and
risks before handing the plan back to the user. The user later approved
the plan plus three follow-up changes ("tighten Background, add
cluster-grouping rules, fold Open Questions into Item 1"), all of which
the critique had recommended.

## Findings (reverse-engineered from the polish diff)

### 1. Background was too long for an orchestration plan

**Severity:** medium.
**Symptom:** the Background section was eight bullets long and re-stated
configuration, entry points, and ten lessons individually — content the
sub-agents would re-read in `tasks/lessons.md` anyway.
**Recommendation accepted:** merge Configuration + Entry points into a
single block, condense the ten-lesson list into a single semicolon-
separated paragraph, and shrink Orchestration mechanics from three
bullets to one sentence. Net Background reduction: ~14 lines.

### 2. Open Questions section was an orphan

**Severity:** medium.
**Symptom:** the original plan placed three Open Questions in their own
top-level section _after_ Item 1, but the sub-agent for Item 1 needed
those answers _before_ doing anything. The orchestrator had to read both
sections and stitch them together.
**Recommendation accepted:** fold Open Questions into Item 1 as **Step
A** (a 4-column decision table) followed by **Step B** (author the
override config). Removed the standalone "Open Questions" section.

### 3. `personal-config`'s 18 open PRs needed cluster-grouping rules

**Severity:** medium-high.
**Symptom:** Item 3 said "process by lane" but didn't specify how to
order PRs _within_ the `personal-config` lane. With 18 open PRs across
five distinct automation patterns (Bolt, Sentinel, Jules QA, Trust
boundary, Red gate), an unguided agent would either serialize blindly
(slow, prone to cascade conflicts per Lesson 0cc) or batch-merge by file
overlap (risky on security-classified items per Lesson 0bb).
**Recommendation accepted:** add a "personal-config cluster discipline"
sub-section to Item 3 with:

- A formal definition of _cluster_ (≥2 shared file paths or shared
  automation source).
- Canonical-PR-first procedure (newest, most-focused, lowest conflict).
- Explicit `update-branch` HTTP 422 disambiguation hook (Lesson 0aa).
- A 5-row table of named clusters (Bolt perf, Sentinel security, Jules
  QA, Trust boundary, Red gate) with likely files and default
  dispositions.
- An explicit "verify cluster membership against live inventory before
  acting" caveat — PR numbers move between plan-time and run-time.

### 4. Item 4 conflated salvage with documentation

**Severity:** low.
**Symptom:** the original Item 4 mixed "open salvage PRs" with "write the
session report and update lessons.md" in a single sub-agent brief.
Different sub-agent roles fit those two tasks (salvage is `pair`,
documentation is `engineer`).
**Recommendation accepted:** split Item 4 into 4A (`pair` — salvage
execution, branch pushes, draft PRs) and 4B (`engineer` — consolidated
audit trail + session report + verification gates).

### 5. Lesson `0de` was acknowledged but not turned into a runbook step

**Severity:** low (deferred).
**Symptom:** the plan referenced Lesson `0de` (timed-out `agent_run start`
may still be executing) in Background but didn't name a recovery
procedure for the orchestrator. The polish pass added a one-line
reference to "reconcile live state before re-dispatching" inside
Orchestration mechanics, which was deemed sufficient for this run; a
fuller runbook entry was deferred to a future session.

## What the critique did **not** catch (recovery hindsight, 2026-05-10)

The critique focused on plan structure and operational guidance for the
sub-agents, but it did not flag the implicit assumption that **salvage
sub-agents would respect the "no local working-tree manipulation" rule
when their brief mentioned cherry-picking commits.** Item 4A's agent
ran `git checkout <pr-branch>` in the working repo, which destroyed the
untracked `docs/plans/` and `docs/reviews/` directories. The relevant
guard would have been: "**brief salvage agents to do all branch work in
a `git clone` under `/tmp/`, never in the working repo, and commit
important documents _before_ dispatching a salvage agent.**" That guard
is now Lesson `0df` (candidate, pending commit decision).

## Outcome

The polish pass landed all five recommendations (#1–#4 + the deferred
note on #5). The plan moved from 141 lines pre-polish to ≈138 lines
post-polish despite adding the cluster-grouping table. The `<forked_session>`
transcript captured the user's approval ("Everything looks good with the
plan. Could you also help with the follow-ups you suggested?") and the
post-polish self-consistency check ("no orphan references to the removed
section, no broken file:line links, lane order in Approach still matches
Item 3's lane sequencing").
