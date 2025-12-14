## 2025-10-21 - Command Injection in Notification System
**Vulnerability:** Found unsanitized input being passed to `eval` in `smart_notify` function.
**Learning:** Even internal helper scripts can be vulnerable if they construct commands via string concatenation and use `eval`. Inputs like notification titles might come from external sources (logs, filenames) and trigger execution.
**Prevention:** Avoid `eval`. Use direct command execution. If constructing complex arguments, verify quoting or use arrays. For AppleScript, escape quotes and backslashes.
