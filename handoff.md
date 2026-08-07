========== ELIR ==========
PURPOSE: Extracted complex logic into helper functions/constants to pass CodeScene's advisory code health rules (Complex Method and Large Method).
SECURITY: No security implications. This is purely a refactoring for code maintainability.
FAILS IF: The extracted functions or string constants in the benchmarks are not invoked or parsed correctly due to scope changes.
VERIFY: Verify the full unit test suite still passes successfully.
MAINTAIN: When adding new benchmarks or candidate selection rules, aim to keep methods small and focused.
