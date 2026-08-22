# Re-review: three-stage PR lifecycle at `e9cd71c` (request changes)

**PR:** https://github.com/abhimehro/personal-config/pull/2026 **Head
re-reviewed:** `e9cd71c1794751f58ebbe841124e5382a4f3651c` **Previous review
baseline:** `7f1475d627a4d01f1b72732866b4cea1a7820b54` **Base:** `main`
**Diff:** 24 files, +1549/−570 **State:** open, draft, `MERGEABLE` **Checks:**
mostly green; `CodeScene Code Health Review (main)` = **failure**;
`Analyze (swift)` = pending

Thank you, this is a large and genuinely good revision. 13 of the 16 matrix rows
are substantively implemented, and the ledger/handoff/calibration design is now
real engineering rather than prose. I verified each row against the branch
rather than against the summary.

Two findings block merge, and one of them defeats the specific guarantee the
maintainer asked for: that Stage 3 stays in calibration until seven successful
runs plus written approval.

---

## 1. Verdict

**Request changes.** Not because the direction is wrong, but because the
enforcement layer has two proven holes:

- **B1** makes the ledger fail validation the first time any stage writes a real
  evidence URL, which halts the whole lifecycle by contract on day one.
- **B2** lets `calibration.status: APPROVED` validate with
  `successful_run_count: 0`, so the seven-run gate is documentation only.

Both are small patches. Everything else below is cleanup or operational
sequencing.

---

## 2. Matrix re-audit

Verified against `e9cd71c`, not against the status column in
`docs/pr-lifecycle-revision-checklist.md`.

|  # | Requirement                                     | My verification                                                                                                                                                                                                                                            | Verdict                                          |
| -: | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
|  1 | Stage 1 keeps routine approve/merge/close       | `exports/daily-pr-review.json` has `prComment.allowApprove: true`; prompt limits action to identity-verified bot routine work and defers to the merge-method registry                                                                                      | Confirmed                                        |
|  2 | Stage 2 draft-only, no approve/reviewer-request | `exports/daily-pr-salvage.json` actions = GitKraken MCP only; validator asserts no approval and no `requestReviewers`                                                                                                                                      | Confirmed                                        |
|  3 | Stage 3 calibrated, two variants                | Separate calibration and bounded-completion prompts/exports exist and differ in authority                                                                                                                                                                  | Confirmed, but see **B2**                        |
|  4 | Normative machine-readable ledger schema        | `schemas/pr-lifecycle-ledger.schema.json` exists and is thorough                                                                                                                                                                                           | Partial, see **B5**                              |
|  5 | Atomic, idempotent, revision-checked handoffs   | `docs/automated-pr-lifecycle.md` lines 49-55 define event ID, expected revision, CAS, acknowledgement, replay no-op, interrupted-write recovery; validator enforces increment-by-one and `(item_key, event_id)` idempotency                                | Confirmed, good work                             |
|  6 | Durable calibration state and reset rules       | Schema requires status, counts, scope, policy revision, coverage, approver, evidence, invalidation, revocation, rollback, authority                                                                                                                        | Partial, see **B2**                              |
|  7 | Paste-ready prompts and exports                 | Four prompts, four exports, `dashboard-application-checklist.md` with UTC note, environment ID, allowlists, rollback; `sync_cursor_export_prompts.py --check` returns `CURSOR_EXPORT_PROMPTS_MATCH`                                                        | Confirmed                                        |
|  8 | Stage 2 work-item schema                        | `stage2WorkItem` requires anchors, allowed/prohibited paths, test command/result, acceptance criteria, provenance, expiry, attempts, owner, creation event, history; validator rejects incomplete items                                                    | Confirmed                                        |
|  9 | GitHub identity + sticky sensitive paths        | Prompts mandate `login`/`app_slug` from the API, ambiguous-is-human; validator rejects non-BOT with `risk_class: ROUTINE`                                                                                                                                  | Confirmed, nicely enforced                       |
| 10 | Restore or map deleted salvage procedures       | Doc is 141 lines vs 531 on `main`, but adds Steps 0-6 plus a "Migrated legacy procedures" crosswalk that maps trigger detection, deferred-tail intake, infra grouping, trusted base, journal protection, test adaptation, provenance, retry, and rejection | Accepted as mapped                               |
| 11 | Reproducible historical import                  | `docs/automated-pr-lifecycle.md` lines 111-115 define globs, precedence order, fingerprint + `import_id`, rerun skip, legacy status mapping, `EVIDENCE_ONLY` for anchorless records, no resurrection of closed PRs                                         | Confirmed                                        |
| 12 | Mandatory completion/continuity fields          | `tasks/pr-stage-run-record.example.md` plus completion doc reporting section                                                                                                                                                                               | Confirmed                                        |
| 13 | Memory disabled or namespaced                   | `memoryEnabled: false` in all four exports; validator hard-fails otherwise; prompts state memory may never override the ledger                                                                                                                             | Confirmed                                        |
| 14 | Per-repository merge path                       | `repository_merge_methods` registry; personal-config = `TRUNK_QUEUE` / `TRUNK`; completion prompt handles approve-then-queue, partial failure, branch-delete follow-up                                                                                     | Confirmed as a mechanism, see **B7/B8** for data |
| 15 | Least-privilege MCP/actions                     | All four exports attach only GitKraken (id `5021`) plus, where authorized, `prComment`. No browser, Playwright, desktop-commander, AppleScript, mail, drive, calendar, Rube, Firebase, Cloudflare, Clerk                                                   | Confirmed                                        |
| 16 | Numbering and scheduling contradiction          | `docs/automated-pr-review-agent.md` now numbers 1-5 sequentially; 06:00/08:00/08:15 are labeled inputs while 13:00/17:00/21:15 UTC are the lifecycle                                                                                                       | Confirmed                                        |

---

## 3. Blocking defects

### B1. The URL check rejects every real URL, so the ledger breaks on the first written item

`scripts/validate_pr_lifecycle_artifacts.py`:

```python
URL_RE = re.compile(r"^https://")
...
if not isinstance(url, str) or not URL_RE.fullmatch(url):
    raise ValueError(f"ledger item {key}: evidence URLs must use https")
```

`fullmatch` anchors the entire string, so the pattern `^https://` matches only
the literal string `"https://"`. Reproduced:

```
'https://github.com/abhimehro/personal-config/pull/2026'  fullmatch=False  match=True
'https://'                                                fullmatch=True   match=True
```

Consequences:

- `tasks/pr-lifecycle-ledger.example.yaml` **fails its own validator**:
  `PR_LIFECYCLE_INVALID: ledger item abhimehro/personal-config#2026@0123...4567: evidence URLs must use https`
- `tasks/pr-lifecycle-ledger.yaml` passes only because `items: []`, so the code
  path never runs.
- Per `docs/automated-pr-lifecycle.md`, any validation failure is
  `ANALYSIS_ERROR` and no action may follow. So the first Stage 1 run that
  records an item with an evidence URL bricks all three stages until a human
  patches the regex.

Fix: use `URL_RE.match(url)`, or make the pattern `^https://\S+$`. Apply the
same reasoning anywhere a prefix pattern is paired with `fullmatch`. Then
confirm `provenance_urls` and `approval_evidence_urls` are checked with the same
helper, since today only item `evidence_urls` is URL-validated at all.

### B2. `APPROVED` validates with zero successful calibration runs

This is the guarantee the maintainer explicitly asked to keep. It is not
enforced.

`_validate_calibration` checks that `required_successful_runs == 7` and that
`APPROVED` carries an approver, timestamp, and evidence. It never compares
`successful_run_count` to `required_successful_runs`.

Reproduced on a copy of the checked-in ledger, changing only
status/approver/timestamp/evidence and leaving `successful_run_count: 0`:

```
successful_run_count still: 0
PR_LIFECYCLE_VALID
```

So a premature or accidental edit promotes Stage 3 to approve/merge/close
authority with no calibration history, and the validator blesses it.

Required:

- `status == "APPROVED"` requires
  `successful_run_count >= required_successful_runs`.
- `successful_run_count` must not exceed `required_successful_runs` without an
  explicit reset.
- Increments must be traceable to `kind: CALIBRATION` events, and the event
  count for the current `policy_revision` must reconcile with
  `successful_run_count`.
- Any change to prompts, identity list, sensitive-path taxonomy, permission
  scope, required-check source, or merge method must reset
  `successful_run_count` to 0 and set `invalidated_by_revision` — the rollback
  conditions say this, but nothing checks it.
- Add a test for each: `APPROVED` + count 6 fails, count 7 passes, count 7 with
  a stale `policy_revision` fails.

### B3. The terminal-disposition test passes for the wrong reason

`tests/test_pr_lifecycle_artifacts.py::test_terminal_item_requires_terminal_disposition_and_no_owner`
builds its fixture from the example ledger and asserts `ValueError`. Because the
example already fails on **B1**, the assertion succeeds no matter what the
terminal-disposition logic does. The test would still pass if that check were
deleted.

It also contains a no-op:

```python
.replace("terminal_disposition: null", "terminal_disposition: null", 1)
```

Fix: assert on the specific message, or build a minimal valid fixture and mutate
exactly one field.

### B4. Test-count and validation claims do not match the branch

`tests/test_pr_lifecycle_artifacts.py` collects **4 tests**, not 42:

```
4 passed in 0.33s
```

Separately, `CodeScene Code Health Review (main)` is failing on this head and
`Analyze (swift)` is still pending. Please reconcile the claim, and either fix
or explicitly waive the CodeScene delta with a reason. Given the contract states
validation failure equals `ANALYSIS_ERROR`, a failing quality gate on the very
PR that defines the gate is worth resolving before merge.

### B5. The JSON Schema is declared normative but never executed

`docs/automated-pr-lifecycle.md` calls `schemas/pr-lifecycle-ledger.schema.json`
"the normative machine-readable schema." In practice:

- no `jsonschema` import exists anywhere in `scripts/` or `tests/`;
- the only use of the path is a string equality check on
  `ledger["schema_path"]`;
- all real validation is a parallel hand-written implementation.

So the schema and the validator can drift silently, and **B1**/**B2** are
exactly the class of bug that drift produces. Pick one:

1. validate against the schema with `jsonschema`, keeping the hand-written pass
   for cross-field rules the schema cannot express; or
2. add a conformance test that asserts required-field sets and enums in the
   schema equal the constants in the validator (`ITEM_FIELDS`,
   `ALLOWED_OUTCOMES`, `TERMINAL_DISPOSITIONS`, owner and state enums).

Option 1 is preferable; option 2 is acceptable and cheap.

### B6. `tasks/pr-review-agent.config.yaml` still contradicts the new contract

Three legacy keys survive and now conflict with the artifacts in this same PR:

| Key                        | Current value           | Conflict                                                                                           |
| -------------------------- | ----------------------- | -------------------------------------------------------------------------------------------------- |
| `merge_strategy`           | `squash`                | Registry says `abhimehro/personal-config` is `TRUNK_QUEUE`; prompts forbid a raw squash assumption |
| `auto_fix_enabled`         | `true`                  | Stage 1 is no longer an auto-fix agent; bounded repair moved to Stage 2 work items                 |
| `human_escalation_channel` | `github-review-request` | Every prompt forbids reviewer requests, and the validator rejects a `requestReviewers` action      |

Also, the new `lifecycle:` block is still **not consumed or validated**.
`scripts/_load_pr_review_agent_config.py` emits only `repos` and `bot_authors`,
and `validate()` reads the config solely to build `configured_repos`. So
`lifecycle.stage_caps` and `lifecycle.stages.*.authority` can drift from the
prompts and exports with nothing detecting it.

Fix: delete or scope the three legacy keys, and add validator assertions that
`lifecycle.stage_caps` and each `stages.*.authority`/`schedule` agree with the
corresponding prompt text and export cron.

### B7. Six of seven repositories cannot be completed today

`repository_merge_methods` has `method: UNKNOWN` and
`required_checks_source: UNKNOWN` for `ctrld-sync`, `email-security-pipeline`,
`Seatek_Analysis`, `Hydrograph_Versus_Seatek_Sensors_Project`,
`series_correction_project_updated`, and `repoprompt-ce`. Only `personal-config`
is registered.

The prompts require a known merge method and a readable required-check source
before any routine action, and instruct the agent to hold otherwise, which is
correct behavior. The consequence is that on day one Stage 1 and Stage 3 can
complete work in exactly one repository, and the other six accumulate held
items. That is the backlog outcome this workflow exists to prevent.

Fix: populate all seven entries before the first calibration run, or state in
the checklist that discovering and recording each repository's merge method and
required-check source is a prerequisite task, and treat `UNKNOWN` as a tracked
gap rather than a steady state.

### B8. `required_checks: []` is ambiguous

`personal-config` has `required_checks_source: TRUNK` with
`required_checks: []`. A stage told "required checks pass" can read an empty
list as vacuously satisfied and merge with no gate. Define explicitly: an empty
`required_checks` with a readable source means the source must be re-read, and
an unreadable or empty result is `HOLD_PLATFORM`, never a pass. Then populate
the Trunk required set.

---

## 4. Operational risk in applying the exports

Both Stage 3 exports declare the same cron:

```
daily-pr-completion.calibration.json  ->  "15 21 * * *"
daily-pr-completion.json              ->  "15 21 * * *"
```

Their names differ, so the dashboard will happily hold both. If the maintainer
_creates_ the completion automation rather than _replacing_ the calibration one,
two Stage 3 agents run at the same minute against the same ledger, one of them
holding `allowApprove: true`, while calibration is still supposed to be
report-only.

`dashboard-application-checklist.md` says to enable completion only after
approval, but it does not say to remove or disable the calibration automation
first. Please make that explicit and mutually exclusive, and add a note that the
checked-in `lifecycle.stages.*.concurrency: 1` is a documentation intent, not
something the dashboard enforces.

---

## 5. Minor issues

- `UTC_RE = re.compile(r".+Z$")` accepts `"bananaZ"`. The schema's
  `"pattern": "Z$"` is equally weak. Use a real RFC 3339 UTC pattern.
- The validator does not reject `next_owner: none` on a nonterminal item, though
  the contract requires every nonterminal item to carry exactly one next owner.
- `_validate_events` verifies `resulting_item_revision <= item.revision` but
  never that the newest event for an item equals `item.revision`, so a
  projection can silently run ahead of its event log.
- Dead code in `_validate_exports`:
  `.replace("daily-pr-completion.calibration.md", "daily-pr-completion.calibration.md")`.
- Neither `scripts/validate_pr_lifecycle_artifacts.py` nor
  `scripts/sync_cursor_export_prompts.py` is wired into CI in this PR as far as
  I can see. If they are meant to be fail-closed gates, add them to the test
  workflow so a drifted export cannot merge.

---

## 6. Required patch list

1. Fix `URL_RE` usage so real `https://` URLs validate; apply URL validation to
   `provenance_urls` and `approval_evidence_urls`.
2. Make `tasks/pr-lifecycle-ledger.example.yaml` validate, and add a test
   asserting it.
3. Enforce `successful_run_count >= required_successful_runs` for `APPROVED`,
   reconcile the count against `CALIBRATION` events and `policy_revision`, and
   enforce reset on policy change. Add the three calibration tests.
4. Repair `test_terminal_item_requires_terminal_disposition_and_no_owner` so it
   cannot pass for an unrelated reason.
5. Either validate against the JSON Schema or add a schema/validator conformance
   test.
6. Remove or rescope `merge_strategy`, `auto_fix_enabled`, and
   `human_escalation_channel`; validate the `lifecycle:` block against prompts
   and export crons.
7. Populate merge method and required-check source for all seven repositories,
   or record `UNKNOWN` as a tracked prerequisite.
8. Define empty `required_checks` as a hold, not a pass.
9. State in the checklist that the calibration automation must be disabled or
   deleted before the completion automation is enabled.
10. Tighten the UTC pattern, reject `next_owner: none` on nonterminal items, and
    remove the dead `replace`.
11. Resolve or explicitly waive the failing CodeScene delta; correct the
    test-count claim.
12. Wire the validator and export-sync check into CI.

---

## 7. What to do with the dashboard in the meantime

The live 13:00 and 17:00 automations still run the old end-to-end prompts, and
Stage 2 still holds `allowApprove`. Until B1 and B2 are patched, applying the
new exports would deploy a lifecycle whose ledger fails validation on its first
real write.

Recommended sequence, expanded in my accompanying note:

1. Land the patches above.
2. Apply Stage 1 and Stage 2 exports, which removes Stage 2's approve authority
   immediately.
3. Apply the Stage 3 **calibration** export only.
4. Leave `calibration.status: REPORT_ONLY` and let `successful_run_count` reach
   7 through recorded `CALIBRATION` events.
5. Record dated written approval, then swap the calibration automation for the
   completion export.

Great progress on this revision. The remaining work is a handful of targeted
patches to the enforcement layer, not another redesign.
