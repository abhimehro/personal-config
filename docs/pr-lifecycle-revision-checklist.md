# PR Lifecycle Revision Checklist

**Applies to:** `personal-config` PR #2026
**Review baseline:** Head `7f1475d627a4d01f1b72732866b4cea1a7820b54` reviewed against `main` `e11e0b9e`
**Purpose:** This is the implementation and re-review matrix for the maintainer-designated blocking review. It is not a merge authorization. PR #2026 remains a draft until all entries are evidenced and a human re-reviews the complete contract.

## Preserved authority model

The revision must retain the parts of the reviewed design that already match maintainer intent. **Stage 1** remains the evidence-complete routine executor for bot-authored, non-sensitive PRs. **Stage 2** remains a draft-only recovery builder. **Stage 3** remains report-only during a durable calibration gate and becomes a bounded non-security completion layer only after recorded approval. Security-sensitive and ordinary human-authored PRs never enter an automated merge or close path.

| # | Blocking requirement | Required artifact or change | Validation evidence | Status |
|---:|---|---|---|---|
| 1 | Keep Stage 1 routine approve, merge, and close authority. | Stage 1 prompt/export preserves `prComment.allowApprove: true`, limits action to identity-verified bot routine work, and uses the repository merge-method registry. | Export validation plus prompt predicates. | Implemented, validated |
| 2 | Keep Stage 2 draft-only and remove approval/reviewer-request capability. | Stage 2 prompt/export includes no approval or reviewer-request action, accepts only complete Stage 2 work items, and creates drafts/candidates only. | Export action-set validation. | Implemented, validated |
| 3 | Make Stage 3 a calibrated completion layer, not a permanent third reviewer. | Separate calibration and post-calibration prompts/exports; durable approval, rollback, reset, scope, and success-count rules. | Calibration schema and transition validation. | Implemented, validated |
| 4 | Provide a normative machine-readable ledger schema. | JSON Schema, validated YAML ledger, complete terminal/nonterminal/event/calibration/Stage 2-work-item examples, and fail-closed validator. | Validator success and malformed-fixture failure. | Implemented, validated |
| 5 | Make handoffs atomic, idempotent, and revision-checked. | Event ID, expected revision, acknowledgement, idempotency key, compare-and-swap semantics, and interrupted-write recovery procedure. | Lifecycle transition and duplicate-event fixtures. | Implemented, validated |
| 6 | Persist calibration state and reset rules. | Schema fields for scope, policy revision, approval, representative coverage, resets, revocation, and action authority. | Calibration fixture and validator. | Implemented, validated |
| 7 | Supply paste-ready Cursor prompts and actual-surface exports. | Four prompt files, four exports, dashboard create/update checklist, UTC and America/Chicago time note, environment, actions, memory, rollback, and drift check. | JSON parse and prompt/export consistency validation. | Implemented, validated |
| 8 | Define the Stage 2 work-item schema. | Immutable source anchors, allowed/prohibited paths, test command/result, acceptance criteria, provenance, expiry, attempts, owner, and history. | Complete example and validator. | Implemented, validated |
| 9 | Use GitHub identity classification and sticky sensitive paths. | Versioned bot identities, ambiguous-is-human rule, sensitive-path taxonomy, sticky security classification, and calibration invalidation rule. | Prompt and schema validation. | Implemented, validated |
| 10 | Restore or map deleted salvage procedures. | Trigger, source intake, stale-state handling, trusted-base setup, journal safety, bounded recovery, infra diagnosis, branch/provenance, retries, and rejection procedure. | Procedure crosswalk in Stage 2 specification. | Implemented, validated |
| 11 | Make historical import reproducible and rerunnable. | File globs, precedence, deterministic mapping, anchor handling, import ID/event, idempotency, no-longer-open PR handling, and evidence-only rule. | Historical-import procedure and fixture. | Implemented, validated |
| 12 | Require completion and continuity reporting fields. | Mandatory per-item report template with anchors, ownership, identity, classification, audit/action count, live evidence, correctness assessment, outcome, and next state. | Template validation. | Implemented, validated |
| 13 | Disable or namespace shared memory behind the continuity plane. | `memoryEnabled: false` in all reference exports by default, with documented opt-in namespace that cannot override ledger/run records/lessons. | Export and prompt assertions. | Implemented, validated |
| 14 | Make the merge path match each repository. | Merge-method registry declares Trunk, merge queue, direct squash, or unknown; required-check source and unreadable-config hold; audited approval/merge outcomes. | Registry validation and completion predicate. | Implemented, validated |
| 15 | Cut MCP and action access to stage-specific least privilege. | Checked-in allowlists and exports omit browser, desktop, AppleScript, email, drive, reviewer-request, and unrelated tools; write stages restrict their declared GitHub authority. | Export action/MCP allowlist validation. | Implemented, validated |
| 16 | Fix review-spec numbering and scheduled-automation contradiction. | Review specification uses sequential numbering, maps legacy statuses, and identifies the 13:00/17:00/21:15 UTC Cursor runs as the lifecycle; upstream 06:00/08:00/08:15 tasks are inputs only. | Documentation lint and human re-review. | Implemented, validated |

## Re-review gate

Every row must be marked **Implemented** only after its named artifact is present and the stated validation evidence is recorded. A passing documentation check is not evidence that the Cursor Dashboard runtime matches the checked-in source. The maintainer must apply or update the dashboard from the exported artifacts, then record the dashboard fingerprint and the first calibration run in the lifecycle ledger.

## Enforcement-layer follow-up

The approved enforcement follow-up is implemented in source on this draft branch. It adds enforcement, test, and CI coverage without creating a data branch, changing a Cursor Dashboard automation, approving, merging, closing, or otherwise mutating any PR.

| Follow-up | Source implementation | Validation evidence | Runtime status |
|---|---|---|---|
| A1, Git-native ledger write path | `docs/pr-lifecycle-runtime-ledger.md`; main-branch bootstrap pointer; explicit fast-forward and Contents API CAS rules; inventory exclusion; capability hold behavior. | Pointer validation, non-empty runtime fixture, prompt/export validation. | **Deferred:** requires separate post-re-review bootstrap authorization. |
| A2, CodeScene refactor | Validator split into parsing/schema, configuration/export, ledger cross-record, and thin orchestration modules. | Ruff, Bandit, Radon, focused regression suite, fixture validation, prompt/export drift check, and `make test-quick` pass locally; the hosted `CodeScene Code Health Review (main)` passed for enforcement commit `e84816a`. | Source complete, hosted quality gate verified. |
| B1-B2, URL/schema/calibration enforcement | JSON Schema plus cross-record validation for complete HTTPS URLs, timestamps, terminal ownership, projection continuity, current-policy calibration events, and seven-run approval. | Twelve focused regression tests and `PR_LIFECYCLE_VALID`. | Source complete. |
| B3-B4, pointer/registry/config correctness | Runtime pointer validation, legacy-key rejection, exact stage caps/schedules/authorities, verified-zero required-check proof, and dated read-only discovery evidence for all seven repositories. | Fixture validation and targeted regression tests. | Runtime reads remain held until bootstrap. |
| C, Cursor transition and drift safety | Runtime-ledger prompt preamble, prompt/export synchronization, dashboard bootstrap prerequisite, and mutually exclusive Stage 3 transition/rollback steps. | `CURSOR_EXPORT_PROMPTS_MATCH` plus export-action validation. | **Deferred:** no dashboard automation was changed. |
| D, trusted-base enforcement | `Code Quality` CI job installs the pinned schema dependency and runs artifact validation, prompt/export sync, and focused lifecycle tests before the broader suite. | Workflow review and local command parity. | Active when this source reaches the trusted base. |

The broad `make test-all` suite passes. The unrelated `tests/test_controld_manager.sh` false positive was repaired in the test harness by replacing pipefail-sensitive `echo | grep -q` assertions with equivalent Bash here-string checks. The Control D runtime behavior was not changed. The lifecycle smoke suite and focused enforcement suite also pass.
