# Security Policy

## Sensitive Data Handling

- Do not commit secrets (API keys, OAuth tokens, access/refresh tokens) or personal data.
- Use 1Password or environment variables for configuration. Provide `.env.example` only.
- Set `CTRLD_PROFILE_ID` for DNS configs via environment.

## Secret Exposure Response

1. Revoke exposed credentials immediately at the provider.
2. Rotate credentials and update environment storage.
3. Sanitize repository history using `git-filter-repo` and force-push.
4. Open a brief post-incident note describing scope and remediation.

## Reporting a Vulnerability

Open a private security advisory or contact the maintainers through the repository's private channels.
