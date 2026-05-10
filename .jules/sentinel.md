## 2025-02-23 - Command Injection via `eval` in Bash Arrays
**Vulnerability:** Command injection risk when using `eval` to access dynamically named array contents. Even with validation, `eval` creates a structural risk.
**Learning:** Legacy Bash idioms often rely on `eval` for dynamic referencing. Using Bash 4.3+ `declare -n` (nameref) is safer and provides robust structural protection while preventing crashes if input validation is preserved.
**Prevention:** Always prefer `declare -n` for dynamic variable and array referencing instead of `eval`, and ensure input validation handles invalid strings gracefully to prevent nameref initialization errors from crashing the script.
