## 2026-02-08 - Explicit Defaults in Interactive CLIs
**Learning:** When offering a default option in a CLI prompt (e.g., "Enter for Default"), explicitly setting the default value in code (var=${var:-default}) is safer and more robust than relying on empty string matching.
**Action:** Use parameter expansion to set defaults before processing switch logic to prevent "false affordances" where the UI promises a default but the code doesn't strictly enforce it.

## 2026-02-18 - Smart Defaults in CLI Tools
**Learning:** Users often run task-based scripts (like downloaders) with the intent already in their clipboard. Detecting this intent reduces friction.
**Action:** When creating CLI tools that take a single primary input, check if the input can be safely inferred from the clipboard (e.g. `pbpaste`) when running interactively.

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

## 2024-05-24 - CLI Output Scanability
**Learning:** For long-running maintenance scripts, users scan summary tables for failures and outliers (long durations). Standardizing column widths and using semantic colors (Red/Green) significantly reduces cognitive load.
**Action:** Implement fixed-width summary tables with ANSI colors and duration tracking for all batch processing scripts.

## 2026-02-18 - Contextual Menus in CLI
**Learning:** Static menus force users to remember their current state. Dynamic menus that highlight the active configuration (e.g., via checkmarks) transform a tool from a "switcher" to a "dashboard".
**Action:** When building selection menus for toggleable states, always compute and display the current active state inline.

## 2026-03-01 - Visual Feedback for Async Operations
**Learning:** In conversational CLIs, the gap between user input and assistant response can feel like a freeze. A simple loading spinner reassures the user that the system is working, especially during network calls.
**Action:** Implement a lightweight, text-based spinner for any CLI operation that involves variable latency (e.g., API calls).

## 2025-02-17 - Delightful Data Visualization in CLI
**Learning:** In text-based interfaces, mapping abstract data (like weather conditions or time) to relevant emojis provides immediate visual recognition and delight, acting as a "micro-UX" improvement.
**Action:** When displaying categorical data in CLI tools, consider using emoji mappings to enhance scanability and user experience.
## 2025-05-15 - CLI Micro-Interactions
**Learning:** Even simple CLI tools benefit significantly from "web-like" UX patterns: clear headers, explicit loading states ("Thinking..."), and graceful exit handling (Ctrl+C). Users expect feedback for every action, including empty input.
**Action:** Always add a SIGINT handler to CLI tools to restore cursor state and say goodbye. Use box-drawing characters for CLI headers to frame the experience.

## 2026-02-23 - Contextual Delight in CLI
**Learning:** Adding variable feedback (e.g., random loading messages) and contextual greetings transforms a utilitarian tool into a delightful experience, reducing perceived latency.
**Action:** When implementing loading states or startup banners, consider using dynamic text based on time or random selection to add personality.
