# Palette

## 2026-05-20 - Forgiving CLI Menus

**Learning:** Users make typos; exiting on error frustrates them. **Action:**
Loop on invalid input in interactive menus.

## 2026-02-08 - Explicit Defaults in Interactive CLIs

**Learning:** When offering a default option in a CLI prompt (e.g., "Enter for
Default"), explicitly setting the default value in code (var=${var:-default}) is
safer and more robust than relying on empty string matching. **Action:** Use
parameter expansion to set defaults before processing switch logic to prevent
"false affordances" where the UI promises a default but the code doesn't
strictly enforce it.

## 2026-02-18 - Smart Defaults in CLI Tools

**Learning:** Users often run task-based scripts (like downloaders) with the
intent already in their clipboard. Detecting this intent reduces friction.
**Action:** When creating CLI tools that take a single primary input, check if
the input can be safely inferred from the clipboard (e.g. `pbpaste`) when
running interactively.

## 2026-01-20 - Visibility of Invisible States

**Learning:** Users managing network privacy tools (VPN, DNS) need explicit
confirmation of connection states. Assuming "configuration applied" equals
"connected" leads to false security. **Action:** When reporting status for
connectivity tools, always verify the actual interface state (e.g., `utun`
existence) rather than just the configuration intent.

## 2026-01-19 - Consistent Visual Language in CLI Tools

**Learning:** Users perceive a collection of scripts as a cohesive "suite" when
they share visual patterns (colors, emojis, log formats). Inconsistent output
styles make tools feel disjointed and harder to scan. **Action:** When modifying
a script in a suite (like `scripts/`), audit sibling scripts to copy their
logging helpers and color definitions for a unified experience.

## 2026-01-17 - Interactive CLI UX

**Learning:** Adding an interactive selection menu with `select` and `mapfile`
transforms a CLI tool from a "guess the command" experience to a self-guided
interface. **Action:** When improving CLI scripts, prioritize interactive
defaults over error messages when no arguments are provided.

## 2024-05-23 - Interactive Safety for Setup Scripts

**Learning:** Users often run `setup` scripts without knowing exactly what they
will do. A "Plan of Execution" followed by a confirmation prompt (defaulting to
No) builds trust and prevents accidental system modifications. **Action:**
Always add a summary and confirmation step to destructive or complex setup
scripts.

## 2026-01-21 - Conversational CLI Readability

**Learning:** In chat-based CLI tools, raw text streams make it difficult to
distinguish between user input and system response. Simple color coding (e.g.,
Cyan for user, Green for system) dramatically reduces cognitive load.
**Action:** Always implement distinct visual styles for "You" and "Assistant"
prompts in conversational interfaces to create a clear dialogue structure.

## 2024-05-24 - CLI Output Scanability

**Learning:** For long-running maintenance scripts, users scan summary tables
for failures and outliers (long durations). Standardizing column widths and
using semantic colors (Red/Green) significantly reduces cognitive load.
**Action:** Implement fixed-width summary tables with ANSI colors and duration
tracking for all batch processing scripts.

## 2026-02-18 - Contextual Menus in CLI

**Learning:** Static menus force users to remember their current state. Dynamic
menus that highlight the active configuration (e.g., via checkmarks) transform a
tool from a "switcher" to a "dashboard". **Action:** When building selection
menus for toggleable states, always compute and display the current active state
inline.

## 2026-03-01 - Visual Feedback for Async Operations

**Learning:** In conversational CLIs, the gap between user input and assistant
response can feel like a freeze. A simple loading spinner reassures the user
that the system is working, especially during network calls. **Action:**
Implement a lightweight, text-based spinner for any CLI operation that involves
variable latency (e.g., API calls).

## 2025-02-17 - Delightful Data Visualization in CLI

**Learning:** In text-based interfaces, mapping abstract data (like weather
conditions or time) to relevant emojis provides immediate visual recognition and
delight, acting as a "micro-UX" improvement. **Action:** When displaying
categorical data in CLI tools, consider using emoji mappings to enhance
scanability and user experience.

## 2025-05-15 - CLI Micro-Interactions

**Learning:** Even simple CLI tools benefit significantly from "web-like" UX
patterns: clear headers, explicit loading states ("Thinking..."), and graceful
exit handling (Ctrl+C). Users expect feedback for every action, including empty
input. **Action:** Always add a SIGINT handler to CLI tools to restore cursor
state and say goodbye. Use box-drawing characters for CLI headers to frame the
experience.

## 2026-02-23 - Contextual Delight in CLI

**Learning:** Adding variable feedback (e.g., random loading messages) and
contextual greetings transforms a utilitarian tool into a delightful experience,
reducing perceived latency. **Action:** When implementing loading states or
startup banners, consider using dynamic text based on time or random selection
to add personality.

## 2026-03-04 - [CLI Accessibility: Spinner terminal spam]

**Learning:** Animated CLI spinners using `\r` and interval writes create an
inaccessible "terminal spam" experience for screen readers and CI environments,
reading every single frame update. **Action:** When implementing CLI spinners,
wrap the animation start in a `process.stdout.isTTY` check to ensure it
gracefully falls back to a static "working..." message or no spinner in
non-interactive/accessible environments.

## 2026-03-09 - Transparent Wait States

**Learning:** Hardcoded sleeps without visual feedback create uncertainty; users
don't know if a script is frozen or just taking time. **Action:** Replace
arbitrary `sleep` commands with accessible spinners to provide clear visual
feedback during wait periods.

## 2026-03-28 - Prevent Distracting Cursor Flicker in Spinners

**Learning:** When using loops to implement loading spinners in interactive
shell scripts, the terminal cursor frequently flickers as it redraws the line,
distracting the user and degrading the "micro-UX". **Action:** Hide the terminal
cursor using `tput civis 2>/dev/null || true` before the loop, and restore it
using `tput cnorm 2>/dev/null || true` immediately after the loop (and within
error traps) to ensure a smooth, clean animation.

## 2026-03-30 - Graceful degradation for non-TTY environments

**Learning:** In Node.js CLI tools, unconditional ANSI escape sequences for
cursor manipulation (e.g., `\x1B[?25h`, `\x1B[K`) cause 'terminal spam' in
non-TTY environments, breaking screen readers and cluttering CI logs.
**Action:** Always wrap these in `if (process.stdout.isTTY)` checks to ensure
accessibility and clean output.

## 2026-03-31 - Disable ANSI Colors in non-TTY CLIs

**Learning:** Unconditional ANSI color codes in Node.js CLI tools create severe
"terminal spam" for screen readers and CI environments. Even if a script
conditionally handles interactive features (like a spinner), unconditionally
styling static output (like headers and static messages) still breaks
accessibility. **Action:** Make both cursor manipulation codes and styling
variables (like `COLORS`) strictly conditional on `process.stdout.isTTY` using
ternary operators, ensuring a clean and accessible text fallback.

## 2026-04-10 - Graceful Cleanup of CLI Animations

**Learning:** When interrupting an asynchronous stream (like a CLI loading
spinner) or handling an error, hardcoded prefix strings in the cleanup function
can cause visual artifacts. If the stream starts and fails, or if a user hits
Ctrl+C, they might be left with orphaned text like "Assistant: " hanging on
their terminal prompt. **Action:** Separate terminal clearing logic (e.g.
`clearSpinner`) from content rendering. Only print standard prefixes when the
response actually begins streaming, and ensure error handlers and signal traps
completely clear the line.

## 2026-06-03 - Native OS Notification Fallbacks

**Learning:** When adding optional notifications to CLI scripts (like
`terminal-notifier` on macOS), users without the third-party tool installed miss
out on the UX improvement. **Action:** Always provide a fallback to native OS
notifications (like `osascript -e` on macOS) when using third-party notification
tools to ensure a consistent experience. When passing variables to `osascript`,
ensure double quotes within the variables are properly escaped (e.g.,
`esc_val="${val//\"/\\\"}"`) to prevent syntax errors.

## 2026-06-25 - Graceful Exit Handlers

**Learning:** When users interrupt interactive CLI scripts (like setup scripts)
with `Ctrl+C` (`SIGINT`), abruptly terminating the script without feedback feels
broken and unpolished. **Action:** Always add a `trap` for `SIGINT` to
gracefully catch the interruption, print a clear, polite cancellation message
(e.g., `👋 Setup cancelled by user. Goodbye!`), and exit cleanly with standard
code 130.

## 2024-04-16 - Delaying static prefixes in CLI loading states

**Learning:** Printing static prefixes (like "Assistant:") before a dynamic
spinner completes causes screen reader redundancy and can leave visual artifacts
on the terminal if the process is interrupted before the stream begins.
**Action:** Delay printing static prefixes until the dynamic stream actually
begins, and ensure that signal (SIGINT) and error handlers completely clear the
line using `\r\x1B[K` to prevent orphaned text artifacts upon interruption.

## 2026-05-18 - Graceful Exit Handling in TypeScript CLIs

**Learning:** When adding asynchronous tasks like animated spinners to CLI tools
built in TypeScript/Node.js, users expect the terminal to return to a clean
state if they press `Ctrl+C`. Without a proper `SIGINT` handler, the cursor
remains hidden, and spinner text is left scattered on the prompt. **Action:**
Always attach a `process.on('SIGINT')` event listener that explicitly stops
timers (`clearInterval`), restores the cursor (`\x1B[?25h`), clears the line
(`\r\x1B[K`), and exits cleanly with `process.exit(130)`.

## 2024-05-18 - Require Enter for Confirmation Prompts

**Learning:** Using `read -n 1` for confirmation prompts (e.g.,
`read -p "Continue? (y/n): " -n 1`) allows users to accidentally trigger actions
by bumping a key. Additionally, if a user types "yes" instead of "y", the "es"
and the Enter keystroke are left in the stdin buffer, potentially executing
unintended commands after the script finishes. **Action:** Remove the `-n 1`
flag from `read` prompts to require an explicit Enter press, acting as a safety
confirmation and preventing buffer stuffing. When doing so, also remove any
immediately following `echo` command that was previously used to print the
missing newline.

## 2024-05-19 - Accessible Spinners for Wait States

**Learning:** Hardcoded sleeps without visual feedback create uncertainty; users
don't know if a script is frozen or just taking time. **Action:** Replace
arbitrary `sleep` commands with accessible spinners (e.g., `spinner_wait`
function) to provide clear visual feedback during wait periods, ensuring they
safely handle interrupts and only render in interactive terminals (e.g.,
checking `[ -t 1 ] && -z ${CI-}`) to avoid polluting logs.

## 2026-05-29 - Improve Interactive Prompts and Spinner UX

**Learning:** Using `read -p` without the `-r` flag allows backslashes to escape
characters, which can lead to unexpected behavior in interactive prompts.
Additionally, using `tput civis` and `tput cnorm` to hide/show the cursor during
spinners without checking if the output is an interactive terminal (`[ -t 1 ]`)
or if it's running in CI (`[ -z "${CI-}" ]`) causes unnecessary log pollution
and cursor state bugs in automated environments. **Action:** Always use
`read -r -p` for interactive confirmations, and guard cursor manipulation
commands with `[ -t 1 ] && [ -z "${CI-}" ] && tput civis 2>/dev/null || true`.

## 2024-06-10 - Dashboard HTML Accessibility

**Learning:** Shell scripts generating HTML dashboard need better ARIA support.
Visual health indicators are only conveyed through CSS classes or unicode
characters, and metric cards lack screen reader context. **Action:** Add
explicit `aria-label` to dashboard metric cards and ensure ARIA grouping of
values/labels. Add `aria-hidden="true"` to inner decorative text.

## 2026-06-12 - Accessible HTML structure

**Learning:** This repo has shell and python scripts that generate HTML string.
It follows standard HTML structure and uses standard accessibility practices
like aria-label and aria-hidden on inner emojis. Also, note that color contrasts
standard must follow WCAG AA guidelines. **Action:** When adding HTML in
scripts, stick to accessibility best practices.

## 2026-03-07 - Hide decorative emojis properly

**Learning:** When hiding decorative emojis within text-containing elements
(e.g., `<h3>`), wrap only the emoji in `<span aria-hidden="true">`. Applying a
duplicate `aria-label` to the parent text element unnecessarily overrides the
native inner text for screen readers. **Action:** Only wrap the emoji in
`<span aria-hidden="true">` and remove redundant `aria-label` from parent if it
duplicates the visible text.

## 2026-03-10 - Screen reader accessible emoji headings

**Learning:** When using emojis in headings as visual icons, they can cause
screen readers to read the unicode description of the emoji, breaking the flow
of the section title. We must never use `not isascii()` to detect emoji as that
would incorrectly hide valid non-ASCII text like 'Café'. **Action:** Added a
reusable helper that splits emojis from the text using a strict emoji-range
regex `^([\U0001F000-\U0001FAFF\U00002600-\U000027BF\u2600-\u27BF]+)\s+(.*)$`,
applies an `aria-label` to the heading tag containing just the text, and wraps
the emoji icon in `<span aria-hidden="true">` to hide it from screen readers.
