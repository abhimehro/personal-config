# PR #144 Merge Conflict Resolution Guide

## Overview
PR #144 ("⚡ Bolt: Optimized DoH3 validation grep logic") cannot be merged due to conflicts with the main branch. This guide explains the conflicts and provides the resolution.

## Conflicts Identified

### 1. `.jules/bolt.md`
**Conflict:** Both PR #144 and main added entries at the end of the file.

- **Main branch** added: "2026-01-20 - Shell Script Error Checking Fragility"
- **PR #144** wants to add: "2026-02-15 - Grep Memory Optimization and Regex Precision"

### 2. `scripts/network-mode-verify.sh`
**Conflict:** The DoH3 validation logic (lines 157-172) was modified in both branches.

- **Main branch** kept the original double-grep pipeline approach
- **PR #144** optimized it to a single-pass grep with precise regex

## Resolution Strategy

### Approach: Merge Both Changes
Since both changes are valuable and independent:
1. **Keep BOTH bolt.md entries** (chronological order)
2. **Apply the grep optimization** from PR #144 (it's a clear performance improvement)

## Resolved Files

### .jules/bolt.md
Add the PR #144 entry AFTER the main branch entry:

```markdown
## 2026-01-20 - Shell Script Error Checking Fragility
**Learning:** Relying on `grep` to match specific error strings in a pipeline (e.g., `cmd | grep "fail"`) creates a "success by default" trap. If `cmd` fails with an unexpected error message that isn't in the grep list, the check fails (grep returns 1), leading the script to assume success.
**Action:** Always check the command's exit code first. Only parse the output for specific reasons if the exit code indicates failure, and ensure there is a catch-all `else` block for unexpected errors.

## 2026-02-15 - Grep Memory Optimization and Regex Precision
**Learning:** Reading a file into a variable (`$(grep ...)`) just to pipe it into another `grep` is inefficient (memory usage, subshell overhead) and error-prone with regex. A single `grep` with a precise Extended Regex (e.g., `type = 'doh[^3]`) is faster and safer.
**Action:** Replace `var=$(grep ...); if echo "$var" | grep ...` patterns with direct `if grep -E "pattern" file; then ...`.
```

### scripts/network-mode-verify.sh
Replace lines 157-172 with the optimized version:

```bash
    # Enforce DoH3 at config level when we have a readable config file.
    if [[ -n "$active_config" && -f "$active_config" ]]; then
      # ⚡ Bolt Optimization: Use single-pass grep with precise regex to avoid
      # reading file into memory and spawning subshells/pipes.
      # Regex matches lines where type is 'doh' followed by a non-'3' character (e.g., "type = 'doh2'", "type = 'doha'"),
      # while excluding "type = 'doh3'".
      if grep -Eq '^[[:space:]]*type = '\''doh[^3]' "$active_config" 2>/dev/null; then
        fail "Active profile config ($active_config) contains non-DoH3 DoH upstreams (e.g., entries matching \"type = 'doh[^3]'\")."
        ok=1
      elif grep -Eq '^[[:space:]]*type = '\''doh3'\''' "$active_config" 2>/dev/null; then
        pass "Active profile config ($active_config) uses DoH3-only upstreams."
      else
        warn "Could not find any upstream type=\"doh*\" entries in $active_config; DoH3 validation is partial."
      fi
    else
      warn "Active Control D config file could not be read; skipping DoH3 validation."
    fi
```

## Manual Resolution Steps

If you want to resolve this manually on the PR branch:

```bash
# 1. Checkout the PR branch
git checkout bolt-optimize-grep-validation-9679837601280637187

# 2. Fetch latest main
git fetch origin main

# 3. Merge main into PR branch
git merge origin/main

# 4. Resolve conflicts using the content above
#    Edit .jules/bolt.md to include both entries
#    The script file should already have the optimization from PR #144

# 5. Stage resolved files
git add .jules/bolt.md scripts/network-mode-verify.sh

# 6. Complete the merge
git commit

# 7. Push the resolved branch
git push origin bolt-optimize-grep-validation-9679837601280637187
```

## Testing

The grep optimization has been validated with comprehensive unit tests:
- ✅ Correctly identifies doh3-only configs
- ✅ Detects legacy 'doh' entries
- ✅ Detects other non-doh3 variants (doh2, doha, etc.)
- ✅ Handles configs with no doh entries
- ✅ Correctly identifies mixed configs

## Security Considerations

The regex pattern `^[[:space:]]*type = '\''doh[^3]'` is carefully crafted to:
- Match only 'doh' followed by a non-'3' character
- Avoid false positives from 'doh3' entries
- Use proper POSIX character classes for whitespace

This prevents bypass attacks where someone could use 'doh2' or legacy 'doh' to circumvent DoH3 enforcement.

## Alternative: Rebase Approach

If you prefer a cleaner history:

```bash
git checkout bolt-optimize-grep-validation-9679837601280637187
git rebase origin/main
# Resolve conflicts as described above
git push --force-with-lease origin bolt-optimize-grep-validation-9679837601280637187
```

**Note:** Force push requires proper permissions and should be used carefully.
