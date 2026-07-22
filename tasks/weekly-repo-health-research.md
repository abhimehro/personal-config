# Task Specification: Weekly Repository Health & Housekeeping (Research Repos)

Triggers: launchd:schedule (`com.speedybee.repo-health.research` - Every Tuesday
at 09:00 AM) Actions: start_session: > Perform a comprehensive repository
health, performance, and housekeeping audit of these 3 research repositories: 1.
@abhimehro/series_correction_project_updated
(`/Users/speedybee/dev/series_correction_project_updated`) 2.
@abhimehro/Hydrograph_Versus_Seatek_Sensors_Project
(`/Users/speedybee/dev/Hydrograph_Versus_Seatek_Sensors_Project`) 3.
@abhimehro/Seatek_Analysis (`/Users/speedybee/dev/Seatek_Analysis`)

    Scope & Audit Areas:
    - Code Health & Performance: Technical debt, dead code, overly complex modules, NumPy/Pandas vectorization wins, algorithmic optimizations.
    - Documentation: README accuracy, setup/data-format docs, AGENTS.md accuracy, coverage gaps, missing docstrings.
    - Upkeep & Maintenance: Stale branches (`git branch -r`), outdated dependencies, missing issue/PR templates, broken or stale GitHub Actions workflows.

    Proactive Execution & Draft PR Guidelines:
    - When clear, actionable improvements are identified (vectorization, lint/type-check fixes, workflow repairs, documentation fixes):
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
