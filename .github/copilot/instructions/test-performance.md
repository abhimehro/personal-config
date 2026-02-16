# Test Performance Engineering

Ensure tests run quickly to provide fast feedback loops.

## Best Practices
- **Mocking**: Mock slow external commands (e.g., `networksetup`, `ctrld`) to avoid real system delays.
- **Parallel Testing**: Use `pytest-xdist` for Python tests to run across multiple cores.
- **Incremental Testing**: Only run tests relevant to changed files using `git diff` signals.
- **Clean State**: Use `mktemp -d` for isolated, fast file-system operations.

## Patterns
- Shell unit tests: Use `sed` to extract libraries and mock globals.
- Python tests: Use `unittest.mock` for system-level interfaces.

## Success Metrics
- Full regression suite under 30 seconds.
- Unit tests under 5 seconds.
