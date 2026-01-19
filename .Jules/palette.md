## 2026-01-08 - Terminal Spinner UX
**Learning:** Standard ASCII spinners (`|/-\`) feel dated and don't provide context. Using Braille characters (`⠋⠙...`) creates a smoother animation, and adding an elapsed timer `(3s)` gives users helpful feedback on long-running tasks.
**Action:** When implementing CLI spinners, prefer Braille/Unicode (with ASCII fallback) and include status text/timer to reassure the user the process is alive.

## 2026-01-08 - Glanceable Status Headers
**Learning:** Users shouldn't have to parse multiple data points (Process + DNS + IPv6) to determine system state. A "Mixed/Unknown" state is a valid and helpful signal.
**Action:** Synthesize raw data into a single "Effective Mode" header with distinct color/icon to provide immediate answer to "Am I safe?".
## 2026-01-17 - Interactive CLI UX
**Learning:** Adding an interactive selection menu with `select` and `mapfile` transforms a CLI tool from a "guess the command" experience to a self-guided interface.
**Action:** When improving CLI scripts, prioritize interactive defaults over error messages when no arguments are provided.

## 2024-05-23 - Interactive Safety for Setup Scripts
**Learning:**  Users often run `setup` scripts without knowing exactly what they will do. A "Plan of Execution" followed by a confirmation prompt (defaulting to No) builds trust and prevents accidental system modifications.
**Action:**  Always add a summary and confirmation step to destructive or complex setup scripts.

## 2025-05-24 - Consistent Visual Language in CLI Tools
**Learning:**  Users perceive a collection of scripts as a cohesive "suite" when they share visual patterns (colors, emojis, log formats). Inconsistent output styles make tools feel disjointed and harder to scan.
**Action:**  When modifying a script in a suite (like `scripts/`), audit sibling scripts to copy their logging helpers and color definitions for a unified experience.
