## 2024-05-23 - CLI Feedback Consistency
**Learning:** Users judge the quality of a CLI tool by its visual polish and consistency. The current installer uses plain text while the bootstrap script uses emojis. This inconsistency breaks the "professional" feel.
**Action:** Unify CLI logging helpers across scripts to use consistent emoji prefixes (ℹ️, ✅, ⚠️, ❌) and structured "Plan of Action" summaries. This establishes a stronger brand identity for the toolset.
## 2024-05-23 - [CLI UX Enhancement]
**Learning:** Adding emojis and structured formatting to CLI scripts significantly improves readability and user delight, especially for status checks.
**Action:** When working on CLI tools, always check if the output can be made more human-readable with simple formatting and visual indicators.
## 2025-11-20 - CLI Output Enhancement
**Learning:** Adding emojis and structured formatting (tables, indentation) to shell script output significantly improves readability and user delight, even in a text-based interface. Mocks are essential for verifying visual changes in scripts that rely on system commands (like `networksetup`) unavailable in the dev environment.
**Action:** When working on CLI tools, always check if the output can be "humanized" with emojis and better spacing. Use temporary mocks to verify visual formatting when system commands are missing.
