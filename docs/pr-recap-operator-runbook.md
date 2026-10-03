# Agent-Native PR Recap CLI: Operator Runbook

This guide covers setup, runtime authentication, secret management, local
execution, and the Git pre-push hook for the **Agent-Native PR Recap CLI
(`pr-recap sync`)**.

---

## 1. Overview & Provider-Agnostic Secret Architecture

The `pr-recap` CLI synchronizes Git branch and commit metadata, GitNexus
blast-radius analysis, and GitHub PR lifecycle events with Linear workspace
state.

To adhere to least-privilege security standards, **never store or export
plaintext API keys in your persistent shell profile (`.zshrc`, `config.fish`, or
shell history)**.

### Secret Resolution Order

The CLI resolves the Linear API key at runtime using a provider-agnostic
hierarchy:

```
┌────────────────────────────────────────────────────────┐
│ 1. Environment Variable: LINEAR_API_KEY / LINEAR_TOKEN  │ (CI / containers / override)
└──────────────────────────┬─────────────────────────────┘
                           │ If unset
┌──────────────────────────▼─────────────────────────────┐
│ 2. 1Password CLI: op://Personal/LINEAR_API_KEY/credential │ (Primary local provider)
└──────────────────────────┬─────────────────────────────┘
                           │ If unavailable or locked
┌──────────────────────────▼─────────────────────────────┐
│ 3. Proton Pass CLI: Personal / LINEAR_API_KEY / Secret │ (Fallback provider)
└──────────────────────────┬─────────────────────────────┘
                           │ If none resolve
┌──────────────────────────▼─────────────────────────────┐
│ 4. Clear Actionable Error (or Dry-Run Mode)            │
└────────────────────────────────────────────────────────┘
```

### Security Invariants

- **No Secret Leakage**: The key is never logged, echoed, or included in error
  traces (only the source name, e.g. `1password` or `environment`, is emitted).
- **No Secrets on Disk**: Plaintext keys are never written to disk or tracked in
  version control.
- **Reliable Timeouts**: Secret lookups default to 8.0s
  (`PR_RECAP_KEY_TIMEOUT=8.0`) to comfortably accommodate macOS desktop app
  biometrics/IPC handshake (~4.5s) while preventing hanging.

---

## 2. Provider Setup

### Option 1: 1Password CLI (`op`) — Recommended

The 1Password CLI provides seamless integration with macOS Touch ID / Apple
Watch biometric unlock via the desktop app.

#### A. Installation

If not already installed via Homebrew:

```bash
brew install --cask 1password-cli
```

#### B. Connect Desktop App

1. Open the 1Password desktop app.
2. Go to **Settings > Developer**.
3. Check **Integrate with 1Password CLI**.
4. Check **Use biometric unlock** (Touch ID / Apple Watch).

#### C. Store the Secret in 1Password

Create an item in your **Personal** vault:

- **Vault:** `Personal`
- **Title:** `LINEAR_API_KEY`
- **Field Name:** `credential` (or Password / Text)
- **Value:** `lin_api_...`

Secret Reference URI:

```
op://Personal/LINEAR_API_KEY/credential
```

#### D. Verify CLI Access

Run in your terminal (prompts for Touch ID or unlocks immediately):

```bash
op read "op://Personal/LINEAR_API_KEY/credential"
```

---

### Option 2: Proton Pass CLI (`pass-cli`) — Fallback

The Proton Pass CLI is installed locally at `~/.local/bin/pass-cli`.

#### A. Installation & Session Setup

Verify `pass-cli` is available:

```bash
pass-cli --version
```

Log in to your account:

```bash
pass-cli login
```

#### B. Store the Secret in Proton Pass

Create an item in your **Personal** vault:

- **Vault:** `Personal`
- **Title:** `LINEAR_API_KEY`
- **Field Name:** `Secret`
- **Value:** `lin_api_...`

#### C. Verify CLI Access

```bash
pass-cli item view --vault-name "Personal" --item-title "LINEAR_API_KEY" --field "Secret"
```

---

## 3. Configuration File (`.pr-recap.json`)

The repository includes
[`.pr-recap.json`](file:///Users/speedybee/dev/personal-config/.pr-recap.json)
configuring team settings and secret references:

```json
{
  "teamId": "ABHI",
  "stateMap": {
    "inProgress": "031c40d8-acc9-4d31-b5f7-ca9efb7206a1",
    "inReview": "7fe5ca3c-51b1-434b-870b-11e6bb92257b",
    "done": "f7acb293-01d7-4339-953f-9a9ddbfb7de1",
    "todo": "04deb3a6-65ae-41ba-b766-e7b9bf091c8b"
  },
  "commentAnchor": "<!-- pr-recap-agent-summary -->",
  "secretReferences": {
    "onepassword": "op://Personal/LINEAR_API_KEY/credential",
    "protonpass": {
      "vault": "Personal",
      "item": "LINEAR_API_KEY",
      "field": "Secret"
    }
  }
}
```

---

## 4. Execution Patterns (No Plaintext Exports)

### Method 1: Automatic Resolution (Preferred & Zero-Config)

Simply execute `pr-recap sync`. The CLI automatically queries 1Password (or
Proton Pass), resolves the key in ~4-5s, and executes with no shell environment
exports:

```bash
# Preview what would be synced based on current branch / commits (safe no-op if no issues found)
pr-recap sync --dry-run

# Preview sync for a specific target issue in your Linear workspace
pr-recap sync --issue ABHI-2516 --dry-run

# Specify an explicit relationship override
pr-recap sync --issue ABHI-2516:closes --dry-run

# Live synchronization against a specific issue or PR
pr-recap sync --issue ABHI-2516
```

### Method 2: Process-Lifetime Environment Injection (`op run`)

Injects `LINEAR_API_KEY` strictly for the lifetime of the `pr-recap` subprocess
using
[`.env.pr-recap.template`](file:///Users/speedybee/dev/personal-config/.env.pr-recap.template):

```bash
# 1Password CLI injection
op run --env-file=.env.pr-recap.template -- pr-recap sync

# Proton Pass CLI injection
pass-cli run --env-file=.env.pr-recap.template -- pr-recap sync
```

### Method 3: Subshell / On-Demand Read

Fetches the key directly into a single command invocation without modifying your
shell state:

```bash
# Using 1Password
LINEAR_API_KEY="$(op read --force 'op://Personal/LINEAR_API_KEY/credential')" pr-recap sync

# Using Proton Pass
LINEAR_API_KEY="$(pass-cli item view --vault-name 'Personal' --item-title 'LINEAR_API_KEY' --field 'Secret')" pr-recap sync
```

---

## 5. Agent-Generated PRs & Linear Agent Mirrored Issues

If PRs are opened by bots or agents (e.g. Jules, CodeRabbit, Devin, Sentinel,
Bolt, Palette, Dependabot) with irregular branch names (e.g.
`palette/a11y-role-status-...` or `sentinel-fix-pgrep-...`), `pr-recap` resolves
them **completely automatically** without manual `--issue` entry:

1. **Expanded Branch Matching**: Any branch prefix (e.g. `sentinel/ABHI-500`,
   `palette/ABHI-600`, `devin/ABHI-700`, `ABHI-800-desc`) matches the issue key
   directly.
2. **GitHub Closing Issues (`Fixes #123`, `Closes #123`)**: When PRs or commits
   reference a GitHub issue, `pr-recap` queries Linear's attachment index.
   Because **Linear Agent** mirrors GitHub issues to Linear with an attachment
   URL (`https://github.com/.../issues/123`), the corresponding Linear issue
   (`ABHI-xxxx`) is discovered instantly.
3. **Linear Agent PR Attachments (`pull/<number>`)**: When Linear Agent has
   already linked the GitHub PR to Linear, querying Linear by PR number or URL
   automatically resolves the mapped Linear issue.
4. **Local PR Detection via `gh` CLI**: When running `pr-recap sync` on any
   checked-out branch, the CLI queries `gh pr view` to fetch the PR title, body,
   and closing issue references automatically.

---

## 6. Git Pre-Push Hook Integration

The pre-push hook runs automatically before `git push`, analyzing the current
branch, unpushed commits, and linked Linear issues.

### Installation

Symlink the hook to your local Git directory:

```bash
ln -sf ../../scripts/git-hooks/pre-push-pr-recap.sh .git/hooks/pre-push
```

### How the Hook Operates

1. **Zero-Export Secret Fetching**: The hook runs `pr-recap sync --pre-push`.
   The CLI resolves the key via 1Password desktop app background IPC or Touch
   ID.
2. **Non-Interactive & Headless Protection**: `PR_RECAP_KEY_TIMEOUT=8.0` ensures
   the hook has sufficient time for Touch ID/IPC while preventing non-TTY hangs.
3. **Non-Blocking Fallback**: If the vault is locked or secret resolution fails,
   the hook prints an informative notice and allows your `git push` to complete
   uninterrupted.
4. **Strict Enforcement (Optional)**: To strictly require a successful sync
   before pushing:
   ```bash
   STRICT_PR_RECAP=1 git push
   ```
5. **Hook Bypasses**:
   - Native Git: `git push --no-verify`
   - Hook Flag: `PR_RECAP_SKIP=1 git push` or `SKIP_PR_RECAP=1 git push`

---

## 7. Provider Tradeoffs

| Capability                   | 1Password (`op`)                                                                                                           | Proton Pass (`pass-cli`)                                                                                   |
| :--------------------------- | :------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------- |
| **Biometric Integration**    | **Native Touch ID / Watch**: Integrated with macOS desktop app daemon via IPC. Works in terminal without typing passwords. | **Limited**: Requires terminal login session or Personal Access Token (PAT). No native macOS Touch ID IPC. |
| **Non-Interactive Headless** | Supported via 1Password Service Account (`OP_SERVICE_ACCOUNT_TOKEN`).                                                      | Supported via `PROTON_PASS_PERSONAL_ACCESS_TOKEN`.                                                         |
| **Process Secret Injection** | `op run --env-file=... -- cmd` (Masks secrets in stdout/stderr).                                                           | `pass-cli run --env-file=... -- cmd` (Masks secrets).                                                      |
| **Ecosystem Maturity**       | Highly mature, industry standard, broad CI/CD plugin support.                                                              | Fast-evolving, newer CLI ecosystem.                                                                        |
| **Recommendation**           | **Primary choice** for daily local developer workflow on macOS.                                                            | **Solid secondary fallback** or isolated agent vault.                                                      |

---

## 8. Troubleshooting

### 1Password: `could not read secret: error initializing client: connecting to desktop app`

- **Cause:** The 1Password desktop app is closed or CLI integration is disabled.
- **Fix:**
  1. Open 1Password app.
  2. Ensure **Settings > Developer > Integrate with 1Password CLI** is checked.
  3. Ensure 1Password is unlocked with Touch ID or master password.

### 1Password: `item not found`

- **Cause:** The vault name, item title, or field label does not match.
- **Fix:** Run `op item get "LINEAR_API_KEY" --vault "Personal"` to inspect
  available field labels. Update `.pr-recap.json` if using a custom label.

### Proton Pass: `Error finding vault [Personal]: Error listing vaults`

- **Cause:** The Proton Pass CLI session has expired or is unauthenticated.
- **Fix:** Run `pass-cli login` to authenticate the session, or set
  `PROTON_PASS_PERSONAL_ACCESS_TOKEN`.

### Git push hangs or delays

- **Cause:** A password manager is waiting for an interactive prompt on a
  non-TTY terminal.
- **Fix:** The pre-push hook enforces `PR_RECAP_KEY_TIMEOUT=8.0`. To bypass
  immediately, run `git push --no-verify` or `PR_RECAP_SKIP=1 git push`.

### `No Linear API key resolved... Dry-run mode will plan without network mutations`

- **Cause:** `PR_RECAP_KEY_TIMEOUT` expired before the password manager desktop
  app could respond (on macOS, biometric unlock and local IPC take ~4.5
  seconds).
- **Fix:** Ensure the 1Password desktop app or Proton Pass session is active. If
  your hardware needs slightly more time, pass
  `PR_RECAP_KEY_TIMEOUT=10.0 pr-recap sync --dry-run`.

### `Linear issue 'XXX-#' not found in workspace`

- **Cause:** An issue key was detected from git history or branch name that does
  not exist in your Linear workspace, or was matched from a non-issue string
  (e.g. software version numbers like `pre-3.12` or `v2-1.0`).
- **Fix:** The CLI now enforces strictly uppercase issue keys
  (`\b[A-Z]{2,10}-\d+\b`) and ignores decimal version numbers. To target a known
  issue explicitly, pass `--issue <KEY>`, e.g.:
  ```bash
  pr-recap sync --issue ABHI-2516 --dry-run
  ```
