## 2024-05-23 - Shell Script Cross-Platform Performance
**Learning:** Checking for OS-specific commands (like `stat` on macOS vs Linux) inside a loop or frequently called function by trying one then the other (e.g., `cmd1 || cmd2`) is inefficient. It forces the shell to fork and execute a failing process every time on the "secondary" platform.
**Action:** Detect the OS or command capability ONCE at the start of the script, define a function or variable for the correct command, and use that throughout. This saves N-1 process executions.
