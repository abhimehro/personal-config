# Credential Rotation & History Sanitization

## Immediate Rotation

- Revoke and rotate any credentials that were stored in the repository.
- Update values in 1Password or environment management. Never commit secrets.

## Repository Sanitization

```
# Install git-filter-repo if needed
pipx install git-filter-repo || python3 -m pip install --user git-filter-repo

# Example: remove sensitive files and rewrite history
python3 -m git_filter_repo --invert-paths --paths-from-file .sensitive-paths.txt

# Replace emails/usernames across history
cat > replace-text.txt <<'TXT'
old@example.com==>redacted@example.com
abhimehro==>redacted
TXT
python3 -m git_filter_repo --replace-text replace-text.txt

# Force push sanitized history (coordinate with collaborators)
git push --force --tags origin main
```

## Verification

- Re-run secret scans on the new history.
- Verify no personal data or secrets remain in code or commit messages.

## Post-Rotation

- Update application configs to use the new rotated credentials.
- Confirm access logs show no abuse of revoked credentials.

## WebDAV (media server / Infuse)

The live WebDAV password is stored in 1Password as a **Login** item:

- Vault: `Personal`
- Item: `MediaServer`
- Fields: `username`, `password` (read at runtime via `op read op://Personal/MediaServer/...`)

An optional local fallback file (`~/.config/media-server/credentials`) may exist for recovery; it is gitignored and must never be committed.

### Rotate (macOS, interactive)

Prerequisites: [1Password CLI](https://developer.1password.com/docs/cli/get-started/) installed and signed in (`eval "$(op signin)"`).

```bash
# Preview changes
./media-streaming/scripts/rotate-media-webdav.sh --dry-run

# Rotate password in 1Password; sync local fallback file if it already exists
./media-streaming/scripts/rotate-media-webdav.sh

# Also refresh legacy document backup and restart LaunchAgent
./media-streaming/scripts/rotate-media-webdav.sh \
  --sync-legacy-document \
  --restart-media
```

After rotation:

1. Update **Infuse** (and any other WebDAV clients) with the new password from 1Password.
2. Confirm the daemon loads credentials (`media-server-daemon.sh` prefers the fallback file when present, otherwise 1Password).
3. Run a local auth check (replace port if needed):
   `curl -u "infuse:$(op read op://Personal/MediaServer/password)" http://127.0.0.1:8080/`

### Legacy document item

Older backups may use the 1Password **document** titled `Media Server WebDAV Credentials`. Use `--sync-legacy-document` during rotation to keep that document aligned with the Login item, or migrate to the Login item as the single source of truth.
