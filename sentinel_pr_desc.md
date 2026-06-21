🚨 Severity: CRITICAL
💡 Vulnerability: Command Injection (CWE-78) due to `eval` in trap restoration inside `spinner_wait` of `media-streaming/scripts/final-media-server.sh`.
🎯 Impact: Potential arbitrary code execution if an attacker can manipulate trap definitions earlier in the environment.
🔧 Fix: Replaced `eval` trap restoration with an isolated subshell execution.
✅ Verification: Ran `bash -n media-streaming/scripts/final-media-server.sh`, checked script execution, and confirmed `make test-all` passed.
