## 2024-05-29 - Terminal Injection via echo -e
**Vulnerability:** Terminal Injection vulnerability where malicious input containing escape characters could manipulate the terminal display or execute arbitrary commands depending on the terminal emulator. Found in `setup.sh` logging functions.
**Learning:** `echo -e` interpolates escape characters in variables, which is dangerous when outputting untrusted input.
**Prevention:** Use `printf "%b[INFO]%b %s\n"` to strictly separate color formatting (hardcoded via `%b`) from user data (passed via `%s`), preventing execution or interpretation of escape characters within dynamic input.
