🎯 **What:** The `infuse-media-server.py` script previously auto-generated a password and printed it in cleartext to the terminal/console if no password was supplied via CLI arguments or environment variables.

⚠️ **Risk:** Cleartext passwords written to stdout can be inadvertently captured in terminal history, logs, CI/CD outputs, or monitoring systems. This exposes the password and undermines the Basic Authentication protection for the media server.

🛡️ **Solution:** The script now securely prompts for a password using `getpass.getpass()` in interactive mode (TTY). Instead of generating and logging a password, it forces the user to interactively enter a password without echoing it to the screen. If non-interactive mode is used, the script retains its original safe behavior of failing and instructing the user to configure the password appropriately via the environment.

Additionally, to fix a CodeScene Code Health CI failure for "Bumpy Road Ahead" / high cognitive complexity, the password setup logic was refactored by flattening `setup_authentication` into two focused helper functions: `_get_or_generate_user` and `_get_or_prompt_password`.
