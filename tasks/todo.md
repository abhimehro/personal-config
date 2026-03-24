# Automation Expansion & PR Review Maintenance

## 1. Discovery & Verification
- [ ] **Check Jules Daily QA execution status** on `Seatek_Analysis` and `Hydrograph_Versus_Seatek_Sensors_Project`. *Success criteria: Green checkmark on the most recent run.*
- [ ] **Fetch failing step logs** for `repository-automation-daily.yml` (the orchestrator workflow file) in `personal-config` to target the exact `quality-assurance` error configured in `.github/repository-automation.yml` (the config dictionary).

## 2. Infrastructure Cleanup
*Target Repositories: `personal-config`, `email-security-pipeline`, `ctrld-sync`, `Seatek_Analysis`, `Hydrograph_Versus_Seatek_Sensors_Project`*
- [ ] **Remove outright** `.github/workflows/greetings.yml` across all 5 repos.
- [ ] **Remove outright** `.github/workflows/changelog.yml` across all 5 repos.
- [ ] **Verify** no remaining composite actions or workflow dispatches reference the deleted files.

## 3. Workflow Modernization
- [ ] **Draft `release-drafter.yml`** for modern changelog generation, integrating it via independent configs tracking the default `main` branch.
- [ ] **Pin Supply Chain:** Lock `release-drafter/release-drafter` to a specific, verified commit SHA instead of the mutable `@v6` tag.
- [ ] **Update Documentation:** Modify `docs/automated-pr-review-agent.md` directly to explicitly state first-interaction routing is handled by the PR agent.

## 4. Fix personal-config Daily Automation
*(Blocked by Section 1: Proceed only after fetching actionable log data)*
- [ ] Address the `quality-assurance` bottleneck.
- [ ] If relying on a configuration waiver (bypassing the quality gate), ensure the waiver is explicitly documented to expire after 7 days or the next sprint review.

## 5. PR Review Session Execution
- [ ] Execute `scripts/run-pr-review-session.sh` in `personal-config`.
- [ ] Process output into `tasks/pr-inventory.md` and triage using `tasks/pr-triage.md`.
- [ ] Act on the inventory: Squash-merge passing PRs, consolidate trivial updates, and close stalemates.
- [ ] **Ambiguity Catch-all:** Flag ambiguous PRs in `tasks/pr-triage.md` with a `needs-discussion` label for manual resolution in the next cycle.

---
**Security Considerations & Trust Boundaries:**
- **Attack Surface Reduction:** Removing the legacy unmaintained `first-interaction` action shrinks supply-chain exposure.
- **Supply-Chain Hardening:** Pinning `release-drafter` to an immutable commit SHA prevents injection via compromised mutable tags.
- **Least-Privilege Authorization:** The `release-drafter.yml` workflow will be explicitly constrained to `permissions: { contents: write }` (no pull-request write vectors).
- **Assumptions:** The `run-pr-review-session.sh` enforces hard boundaries. No autonomous merges of code failing *Security Gate 2* (as defined in `docs/automated-pr-review-agent.md`) will be permitted. *Zero-diff / superseded* heuristic rules (also defined in `docs/automated-pr-review-agent.md`) will govern closure rationale.
