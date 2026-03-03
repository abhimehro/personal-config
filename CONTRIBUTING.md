# Contributing to personal-config

Thank you for taking the time to contribute! This guide is the single source of
truth for setting up your environment, running the test suite and linter, and
submitting a well-formed pull request.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Development Setup](#development-setup)
3. [Running Tests](#running-tests)
4. [Running the Linter](#running-the-linter)
5. [Running Pre-commit Checks](#running-pre-commit-checks)
6. [Submitting a Pull Request](#submitting-a-pull-request)
7. [Secrets Policy](#secrets-policy)

---

## Prerequisites

| Tool | Minimum version | Install |
|---|---|---|
| macOS | Sequoia 15+ (recommended) | — |
| Homebrew | latest | `https://brew.sh` |
| Git | 2.x | `brew install git` |
| Bash | 5.x | `brew install bash` |
| Python 3 | 3.11+ | `brew install python` |
| Trunk CLI | latest | `brew install trunk-io` |
| 1Password CLI (`op`) | v2+ | `brew install 1password-cli` |

> **Linux / CI:** Most shell tests that touch macOS-specific APIs (launchctl,
> Keychain, 1Password socket) emit `SKIP:` and exit with code 77. The test
> runner treats 77 as a skip, not a failure — so the full suite still passes on
> Linux. See [docs/TESTING.md](docs/TESTING.md) for the complete skip table.

---

## Development Setup

```bash
# 1. Clone the repository
git clone git@github.com:abhimehro/personal-config.git
cd personal-config

# 2. (macOS only) Full idempotent bootstrap — links dotfiles, installs
#    maintenance LaunchAgents, prepares Control D / Windscribe helpers
./setup.sh

# 3. Sync + verify symlinked configs only (skip the rest of setup.sh)
./scripts/sync_all_configs.sh
./scripts/verify_all_configs.sh
```

After cloning you can edit scripts, run linters, and run tests without running
`setup.sh` — the bootstrap step is only needed when you want the symlinks and
LaunchAgents active on your local machine.

---

## Running Tests

### Shell tests (parallel)

```bash
# Run the full suite in parallel (recommended)
make test

# Fast cross-platform smoke tests — ideal before every commit
make test-quick

# Run a single test file
bash tests/test_lib_common.sh
bash tests/test_lib_dns_utils.sh
```

### Python tests

```bash
# All Python tests (stdlib only — no pip install needed)
python3 -m unittest discover -s tests -p 'test_*.py'

# Single module
python3 -m unittest tests.test_path_validation -v
```

### Benchmarks (optional)

```bash
brew install hyperfine   # one-time dependency
make benchmark
```

See [docs/TESTING.md](docs/TESTING.md) for mock patterns, PATH injection, and
the full skip table.

---

## Running the Linter

This repo uses [Trunk](https://docs.trunk.io) as the local lint hub (shellcheck,
shfmt, ruff, black, prettier, trufflehog, and more).

```bash
# Check all files
make lint          # equivalent to: trunk check --all

# Auto-fix where supported
make lint-fix      # equivalent to: trunk fmt
```

> **ShellCheck dual-config note:** `shellcheck` called directly uses
> `.shellcheckrc` (root), while Trunk CI uses `.trunk/configs/.shellcheckrc`
> (`enable=all`). To reproduce CI behaviour locally, run
> `trunk check <file>` instead of calling `shellcheck` directly.

Trunk downloads its own tool versions on first run — subsequent runs are fast.

---

## Running Pre-commit Checks

Before pushing, run the smoke test + lint pass to catch the most common issues:

```bash
make test-quick   # fast cross-platform subset of the test suite
make lint         # full Trunk lint pass
```

If you would like to automate this, install a Git pre-push hook:

```bash
cat > .git/hooks/pre-push <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
make test-quick
make lint
EOF
chmod +x .git/hooks/pre-push
```

---

## Submitting a Pull Request

### Branch naming

| Type | Pattern | Example |
|---|---|---|
| Feature | `feat/<short-description>` | `feat/add-dns-fallback` |
| Bug fix | `fix/<short-description>` | `fix/verify-ssh-perms` |
| Documentation | `docs/<short-description>` | `docs/update-testing-guide` |
| Refactor | `refactor/<short-description>` | `refactor/extract-network-core` |
| Chore / CI | `chore/<short-description>` | `chore/update-trunk-versions` |

Use lowercase, hyphens only, ≤ 40 characters after the prefix.

### What to include in your PR description

Your PR description should answer:

1. **What** — a one-sentence summary of the change.
2. **Why** — the problem being solved or the motivation.
3. **How** — a brief explanation of the approach (especially for non-obvious
   changes).
4. **Testing** — how you verified the change works (`make test`, manual steps,
   etc.).
5. **Security** — any security implications, trust-boundary changes, or
   secrets-handling decisions.

A PR template is pre-filled when you open a pull request on GitHub. Fill every
section; delete sections that genuinely do not apply.

### Checklist before requesting review

- [ ] `make test-quick` passes locally
- [ ] `make lint` reports no new errors
- [ ] No secrets, tokens, or `.env` files are included
- [ ] Documentation updated if behaviour changed
- [ ] PR description filled out completely

---

## Secrets Policy

**Never commit secrets.** This includes API keys, tokens, passwords, private
SSH keys, and any credential that grants access to a system.

| Do | Don't |
|---|---|
| Store secrets in a `.env` file (gitignored) | Commit a `.env` file |
| Use `op run -- <command>` to inject secrets at runtime | Hardcode secrets in scripts |
| Use `.env.example` to document required variables | Put real values in `.env.example` |
| Reference `~/.config/<tool>/credentials` (gitignored) | Track credential files |

The `.gitignore` already excludes `.env`, `.env.*`, `*.secret*`, and several
other secret-bearing paths. Trunk's trufflehog linter scans for accidental
credential exposure on every `make lint` run.

If you accidentally commit a secret, treat it as compromised immediately —
rotate it, then follow the [Security Policy](.github/SECURITY.md).
