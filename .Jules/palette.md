## 2026-01-20 - Visibility of Invisible States
**Learning:** Users managing network privacy tools (VPN, DNS) need explicit confirmation of connection states. Assuming "configuration applied" equals "connected" leads to false security.
**Action:** When reporting status for connectivity tools, always verify the actual interface state (e.g., `utun` existence) rather than just the configuration intent.

## 2026-01-19 - Consistent Visual Language in CLI Tools
**Learning:**  Users perceive a collection of scripts as a cohesive "suite" when they share visual patterns (colors, emojis, log formats). Inconsistent output styles make tools feel disjointed and harder to scan.
**Action:**  When modifying a script in a suite (like `scripts/`), audit sibling scripts to copy their logging helpers and color definitions for a unified experience.

## 2026-01-17 - Interactive CLI UX
**Learning:** Adding an interactive selection menu with `select` and `mapfile` transforms a CLI tool from a "guess the command" experience to a self-guided interface.
**Action:** When improving CLI scripts, prioritize interactive defaults over error messages when no arguments are provided.

## 2024-05-23 - Interactive Safety for Setup Scripts
**Learning:**  Users often run `setup` scripts without knowing exactly what they will do. A "Plan of Execution" followed by a confirmation prompt (defaulting to No) builds trust and prevents accidental system modifications.
**Action:**  Always add a summary and confirmation step to destructive or complex setup scripts.

## 2026-01-21 - Conversational CLI Readability
**Learning:** In chat-based CLI tools, raw text streams make it difficult to distinguish between user input and system response. Simple color coding (e.g., Cyan for user, Green for system) dramatically reduces cognitive load.
**Action:** Always implement distinct visual styles for "You" and "Assistant" prompts in conversational interfaces to create a clear dialogue structure.
