## 2026-01-17 - Interactive CLI UX
**Learning:** Adding an interactive selection menu with `select` and `mapfile` transforms a CLI tool from a "guess the command" experience to a self-guided interface.
**Action:** When improving CLI scripts, prioritize interactive defaults over error messages when no arguments are provided.

## 2024-05-23 - Interactive Safety for Setup Scripts
**Learning:**  Users often run `setup` scripts without knowing exactly what they will do. A "Plan of Execution" followed by a confirmation prompt (defaulting to No) builds trust and prevents accidental system modifications.
**Action:**  Always add a summary and confirmation step to destructive or complex setup scripts.