## 2026-01-08 - Terminal Spinner UX
**Learning:** Standard ASCII spinners (`|/-\`) feel dated and don't provide context. Using Braille characters (`⠋⠙...`) creates a smoother animation, and adding an elapsed timer `(3s)` gives users helpful feedback on long-running tasks.
**Action:** When implementing CLI spinners, prefer Braille/Unicode (with ASCII fallback) and include status text/timer to reassure the user the process is alive.

## 2026-05-21 - CLI UX Robustness
**Learning:** UX enhancements like spinners often lack strict testing. In `set -u` (nounset) environments, a missing variable initialization (like `start_time` in a spinner loop) can crash the entire script, turning a "delight" feature into a critical bug.
**Action:** Always test UX/CLI animation loops with strict bash options (`set -euo pipefail`) to ensure they don't fragility to the main process.
