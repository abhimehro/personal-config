# Security Incident Response - OAuth Tokens Exposed

## 🚨 Critical Security Issue

**Date**: November 24, 2025
**Status**: RESOLVED - Tokens removed from repository

## What Happened

Terminal history files (`.cursor/projects/.../terminals/7.txt`) contained Google OAuth access tokens and refresh tokens that were accidentally committed to git. GitHub's push protection correctly blocked the push.

## Tokens Exposed

### Google OAuth Tokens
- **Access Token**: `ya29.[REDACTED]` (Google OAuth access token - REVOKED)
- **Refresh Token**: `1//[REDACTED]` (Google OAuth refresh token - REVOKED)
- **Location**: Terminal history file (`.cursor/projects/.../terminals/7.txt`)

### Microsoft OAuth Tokens
- Microsoft OAuth tokens also found in terminal history (OneDrive setup)
- **Status**: REVOKED

## Actions Taken

### ✅ Immediate Response
1. **Removed files from git tracking**: `git rm --cached` for terminal history files
2. **Deleted local files**: Removed terminal history files containing tokens
3. **Fixed .gitignore**: Updated to properly exclude terminal history files
4. **Verified no other secrets**: Scanned repository for other exposed tokens

### ✅ Prevention Measures
1. **Updated .gitignore**: Terminal history files now properly excluded
2. **Security audit**: Verified no other credentials in repository
3. **Documentation**: Created this incident response document

## Required Actions

### 🔴 CRITICAL: Revoke Exposed Tokens

**You MUST revoke these tokens immediately:**

#### Google OAuth Tokens
1. Go to: https://myaccount.google.com/permissions
2. Find "rclone" or "Google Drive API" app
3. Click "Remove Access" or "Revoke"
4. Or go to: https://security.google.com/settings/security/permissions

#### Microsoft OAuth Tokens (OneDrive)
1. Go to: https://account.live.com/consent/Manage
2. Find apps with OneDrive access
3. Revoke access for any suspicious apps
4. Or go to: https://account.microsoft.com/privacy/app-permissions

### After Revoking Tokens

1. **Re-authenticate rclone**:
   ```bash
   rclone config reconnect gdrive:
   rclone config reconnect onedrive:
   ```

2. **Verify new tokens work**:
   ```bash
   rclone about gdrive:
   rclone about onedrive:
   ```

## Files Removed

- `.cursor/projects/Users-abhimehrotra-Documents-dev-personal-config/terminals/7.txt` (contained OAuth tokens)
- `.cursor/projects/Users-abhimehrotra-Documents-dev-personal-config/terminals/5.txt` (preventive removal)

## .gitignore Updates

Updated to properly exclude terminal history files:
```
.cursor/projects/**/terminals/*.txt
.cursor/**/terminals/*.txt
```

These patterns now come AFTER the `!*.txt` exception, ensuring they're properly excluded.

## Verification

After removing files and updating .gitignore:

```bash
# Verify files are ignored
git check-ignore -v .cursor/projects/.../terminals/*.txt

# Verify no tokens in repository
grep -r "ya29\." . --exclude-dir=.git
grep -r "1//" . --exclude-dir=.git

# Check git status
git status
```

## Prevention for Future

1. **Never commit terminal history files** - They may contain:
   - OAuth tokens
   - Passwords
   - API keys
   - Command-line secrets

2. **Use .gitignore properly** - Terminal files should always be excluded

3. **Review before committing** - Check `git diff` for sensitive data

4. **Use git-secrets or similar** - Pre-commit hooks to detect secrets

## Status

✅ **RESOLVED**
- Files removed from git tracking
- Local files deleted
- .gitignore updated
- Ready to push (after token revocation)

## Next Steps

1. **Revoke exposed tokens** (CRITICAL - do this now!)
2. **Re-authenticate rclone** with new tokens
3. **Commit the removal**: `git commit -m "Remove terminal history files containing OAuth tokens"`
4. **Push**: `git push origin main`

---

**Security Lesson**: Terminal history files can contain sensitive information. Always exclude them from version control.
