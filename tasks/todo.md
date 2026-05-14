# Vulnerability Fix: Cleartext Password Logging

## Vulnerability Details
- **File:** `media-streaming/archive/scripts/infuse-media-server.py`
- **Line:** 314
- **Vulnerability:** Cleartext password logged to console.
- **Impact:** If the console output is captured by a logging system, CI/CD pipeline, or terminal history, the generated password is exposed in plaintext. This compromises the Basic Authentication mechanism intended to protect the media server.

## Proposed Fix
The generated password should not be printed in plaintext to the console. The current implementation:
```python
        if sys.stdout.isatty():
            alphabet = string.ascii_letters + string.digits
            password = "".join(secrets.SystemRandom().choices(alphabet, k=16))
            print("\n🔒 Security: Authentication Enabled")
            print(f"   User: {user}")
            print(f"   Password: {password}")
            ...
```

Instead of printing it, we can securely prompt the user for a password using `getpass.getpass()`, or just print the password.

Wait, the rationale says: "Clear fix: either don't print the password, or securely prompt for one. Can be easily commented out or replaced."

If we are auto-generating a password, printing it is the only way the user can know what it is if it's generated dynamically, *unless* they pass it in. If it is auto-generated and printed to stdout, it's visible. If it's a daemon, `sys.stdout.isatty()` is false so it fails and asks them to provide it.
But printing secrets to stdout is generally a bad idea if it can be avoided, or if it stays in logs. Since `isatty()` is checked, it only prints to interactive terminals. However, the issue explicitly flags `print(f"   Password: {password}")` as a vulnerability (Cleartext password logged to console).

Let's modify `setup_authentication` so that if a password is not provided:
1. We prompt for it using `getpass.getpass("Enter password for media server: ")`.
2. If the user doesn't enter anything (or if it's not a tty and we fail earlier, but the existing code already handles the not a TTY case), we can generate one. Actually, if it's interactive, we should prompt for the password. If they want it generated, they shouldn't use interactive mode without specifying one. Wait, prompting is more secure.

Let's check `setup_authentication`:
```python
def setup_authentication(args):
    user = args.user or os.environ.get("AUTH_USER")
    password = args.password or os.environ.get("AUTH_PASS")

    generated_user = False
    if not user:
        user_alphabet = string.ascii_lowercase + string.digits
        user = "user_" + "".join(secrets.SystemRandom().choices(user_alphabet, k=8))
        generated_user = True

    if not password:
        if sys.stdout.isatty():
            import getpass
            print("\n🔒 Security: Authentication Enabled")
            print(f"   User: {user}")
            if generated_user:
                print("   (Random username generated. Set custom user via --user)")

            password = getpass.getpass("   Enter password (or leave blank to auto-generate): ")
            if not password:
                alphabet = string.ascii_letters + string.digits
                password = "".join(secrets.SystemRandom().choices(alphabet, k=16))
                # If we auto-generate, we either have to print it or they can't log in!
                # Wait, if we print it, it violates the requirement.
                # Let's just NOT auto-generate passwords. Require the user to type one.
```
Wait, if we use `getpass`, they can just type a password.
```python
            import getpass
            while not password:
                password = getpass.getpass("   Enter password for Basic Auth: ")
                if not password:
                    print("   Password cannot be empty. Please try again.")
            print("   Password set securely.")
```
This is much better. No cleartext password in the terminal.

Let's verify what happens if `user` is generated. It prints `User: user_XXXXXX`. That's fine.
