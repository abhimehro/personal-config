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
