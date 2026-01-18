## 2024-05-23 - [Shell Script Command Injection via Eval]
**Vulnerability:** Found `retry` functions in shell libraries (`common.sh`) using `eval "$cmd"` to execute commands passed as strings.
**Learning:** Shell scripts using `eval` on arguments are highly susceptible to command injection if the arguments are not strictly controlled.
**Prevention:** Avoid `eval` for command execution. Use arrays `"${cmd[@]}"` to store and execute commands. Refactor functions to accept command arguments variadically (e.g., `func args...`) rather than as a single string.
