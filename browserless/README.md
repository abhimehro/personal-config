# Browserless + 1Password + Playwright

Server-side secret resolution for Browserless CDP sessions: Browserless reads
credentials straight from 1Password using a stored service account token, so
secret values never reach automation code, environment variables, or logs.

## Layout

| File | Role | Secrets |
| --- | --- | --- |
| `browserless.env.example` | Configuration template | `op://` references only |
| `templates/browserless-1password-login.mjs` | Playwright CDP template | none (refs passed as args) |
| `scripts/browserless-env.sh` | Runtime secret resolution wrapper | resolved at runtime, never on disk |
| `scripts/browserless-register-1password.sh` | Integration registration helper | resolved at runtime |

## 1Password items (Personal vault)

| Item | UUID | Field | Purpose |
| --- | --- | --- | --- |
| `BROWSERLESS_API_KEY` | `fbbrvhjsd3x7vetbz544uyvjoe` | `credential` | Browserless API key |
| `BROWSERLESS_API_KEY` | `fbbrvhjsd3x7vetbz544uyvjoe` | `key` | 1Password service account token (ops_...) registered with Browserless |

> Note: both secrets live in the single `BROWSERLESS_API_KEY` item (fields
> `credential` and `key`). The old standalone SA-token item
> (`57z7qligy4voo7bjkk444jvfru`) is deprecated; archive it in 1Password when
> convenient.

## Setup

### 1. Register the service account with Browserless

The service account token (ops_...) must be registered with Browserless once.
The helper script is idempotent (re-running prints the existing integrationId):

```bash
scripts/browserless-register-1password.sh
# or with a domain allow-list:
scripts/browserless-register-1password.sh --allow-domain https://app.example.com
```

The output `INTEGRATION_ID=op_int_...` is not a secret; store it in
`browserless.env` (gitignored) or pass it per-run.

### 2. Resolve secrets at runtime

```bash
eval "$(scripts/browserless-env.sh)"
```

Exports `BROWSERLESS_API_KEY` and `OP_SERVICE_ACCOUNTS_TOKEN` into the current
shell, resolved live from 1Password. Nothing is written to disk.

### 3. Run a Playwright session with 1Password fills

```bash
BROWSERLESS_INTEGRATION_ID=op_int_xxx \
node browserless/templates/browserless-1password-login.mjs \
  "https://app.example.com/login" \
  "#email" "#password" "button[type=submit]" \
  "op://Personal/<username-item-uuid>/username" \
  "op://Personal/<password-item-uuid>/password"
```

## Security model

After the first `Browserless.loadSecret` fill, Browserless disables every
channel that could read the value back: screenshots, PDFs, screencasts, live
URLs, page-content reads, and screen recording. Session replay keeps recording
but scrubs filled values. Take any captures **before** the first fill, or in
a separate session.

Recommended pattern: fill credentials once, sign in, then capture the
signed-in state with `Browserless.saveProfile`. Later sessions reuse
`?profile=<name>` with no fill, so captures work normally.

## Failure modes

| Code | Meaning |
| --- | --- |
| `VaultUnreachable` | Browserless could not reach 1Password or the SA token failed auth |
| `CredentialNotResolved` | Wrong vault/item/field, or the SA cannot read it |
| `DomainNotAllowed` | Origin not https, private address, or not on the allow-list |
| `CredentialIntegrationExpired` | SA token expired/revoked — rotate in 1Password |
| `SelectorNotFound` | targetSelector matched no element |
| `TargetNotFillable` | Target is not a fillable input/textarea |
| `NoFocusedElement` | No selector given and nothing focused |
| `AuditWriteFailed` | Fill refused (fail-closed) because audit record could not be written |

## Rotation

- Browserless API key: rotate in the Browserless dashboard, update the
  `BROWSERLESS_API_KEY` 1Password item.
- 1Password service account token: rotate in 1Password, update the
  `browserless_service_account` item, then re-run
  `scripts/browserless-register-1password.sh` (delete the old integration first
  if the label changed).
