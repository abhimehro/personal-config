## 2026-01-08 - Terminal Spinner UX
**Learning:** Standard ASCII spinners (`|/-\`) feel dated and don't provide context. Using Braille characters (`⠋⠙...`) creates a smoother animation, and adding an elapsed timer `(3s)` gives users helpful feedback on long-running tasks.
**Action:** When implementing CLI spinners, prefer Braille/Unicode (with ASCII fallback) and include status text/timer to reassure the user the process is alive.
