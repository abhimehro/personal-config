# Task Specification: Weekly Repository Health & Housekeeping (General Repos)

Triggers: launchd:schedule (`com.speedybee.repo-health.general` - Every Thursday
at 09:00 AM) Actions: start_session: > Perform a comprehensive repository
health, performance, and housekeeping audit of these 4 general repositories: 1.
@abhimehro/personal-config (`/Users/speedybee/dev/personal-config`) 2.
@abhimehro/email-security-pipeline
(`/Users/speedybee/dev/email-security-pipeline`) 3. @abhimehro/ctrld-sync
(`/Users/speedybee/dev/ctrld-sync`) 4. @abhimehro/repoprompt-ce
(`/Users/speedybee/dev/repoprompt-ce`)

    Scope & Audit Areas:
    - Code Health & Performance: Technical debt, dead code, complex modules, performance quick-wins, refactoring opportunities.
    - Documentation: README, setup docs, AGENTS.md accuracy, coverage gaps, outdated guidance.
    - Upkeep & Maintenance: Stale branches (`git branch -r`), outdated dependencies, missing templates, broken or stale GitHub Actions workflows.

    Proactive Execution & Draft PR Guidelines:
    - When clear, actionable improvements are identified (bug fixes, lint/format repairs, workflow updates, doc fixes):
      1. Create a dedicated topic branch: `repo-health/fix-<short-description>`.
      2. Apply clean, minimal changes and verify locally with unit tests/linters.
      3. Open a **Draft PR** with a clear description linking back to the audit findings.
    - **Safeguards (from docs/automated-pr-review-agent.md)**:
      - Never autonomously merge any PRs.
      - Never modify auth, security, credentials, or core database schemas without explicit human approval.

    Deliverable:
    A single, prioritized markdown report appended to `tasks/review-session-reports.md` (and printed to log stdout):
    - Grouped by repository.
    - Each finding formatted as: `[High/Medium/Low] <description> (<file/branch reference>)`
    - List of created Draft PRs (if any).
    - Conclude with a brief 'Suggested Next Actions' section.
