# Bolt's Journal ⚡

## 2024-05-23 - [Initial Entry]
**Learning:** This journal tracks critical performance learnings to avoid repeating mistakes or to document codebase-specific performance patterns.
**Action:** Always check this file before starting performance work to align with past learnings.

## 2024-05-23 - [Initial Setup]
**Learning:** This journal tracks critical performance learnings to avoid repeating mistakes.
**Action:** Always check this file before starting optimization work.

## 2024-05-23 - Shell Script Cross-Platform Performance
**Learning:** Checking for OS-specific commands (like `stat` on macOS vs Linux) inside a loop or frequently called function by trying one then the other (e.g., `cmd1 || cmd2`) is inefficient. It forces the shell to fork and execute a failing process every time on the "secondary" platform.
**Action:** Detect the OS or command capability ONCE at the start of the script, define a function or variable for the correct command, and use that throughout. This saves N-1 process executions.

## 2025-10-26 - Shell Script Polling Optimization
**Learning:** Replaced arbitrary `sleep` calls (2-3s) with polling loops (checking process/file status) in CLI tools.
**Action:** Always prefer active polling with timeout over `sleep` in shell scripts for faster, more reliable execution.
