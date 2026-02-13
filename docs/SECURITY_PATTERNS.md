# Security Patterns and Best Practices

This document outlines security patterns and defensive coding practices used throughout this repository. These patterns help prevent common vulnerabilities and provide defense-in-depth.

## Table of Contents
1. [Symlink Attack Prevention](#symlink-attack-prevention)
2. [TOCTOU Race Condition Mitigation](#toctou-race-condition-mitigation)
3. [File Permission Hardening](#file-permission-hardening)
4. [Command Injection Prevention](#command-injection-prevention)
5. [Path Traversal Protection](#path-traversal-protection)
6. [Credential Security](#credential-security)

---

## Symlink Attack Prevention

### Problem: [CWE-59](https://cwe.mitre.org/data/definitions/59.html) - Improper Link Resolution Before File Access

Symlink attacks occur when an attacker creates a symbolic link at a location where a privileged script expects to create or modify a file. If the script follows the symlink, it may overwrite or change permissions on an unintended target file.

### Vulnerable Pattern ❌

```bash
# BAD: Multi-step operations create TOCTOU windows
rm -f /etc/app/config.conf
cp new_config.conf /etc/app/config.conf
chmod 600 /etc/app/config.conf

# BAD: mkdir + chmod is not atomic
mkdir -p /etc/app/profiles
chmod 700 /etc/app/profiles
```

**Attack scenario:**
1. Script runs `rm -f /etc/app/config.conf`
2. **Attacker quickly creates symlink:** `ln -s /etc/passwd /etc/app/config.conf`
3. Script runs `cp new_config.conf /etc/app/config.conf` → overwrites `/etc/passwd`!

### Secure Pattern ✅

```bash
# GOOD: Atomic file installation
# install -m replaces symlinks with real files atomically
install -m 600 new_config.conf /etc/app/config.conf

# GOOD: Atomic directory creation with permissions
# Note: install -d DOES follow symlinks, so pre-flight checks are essential
install -d -m 700 /etc/app/profiles
```

### Defense-in-Depth Implementation

Our implementation uses multiple layers of protection:

```bash
# Layer 1: Pre-flight symlink checks (all critical paths)
check_not_symlink() {
    local path="$1"
    if [[ -L "$path" ]]; then
        log_err "Security: Refusing to operate on symlink: $path"
        return 1
    fi
    return 0
}

# Layer 2: Check parent directory isn't a symlink
check_not_symlink "$(dirname "$TARGET_PATH")"

# Layer 3: Atomic operation
install -m 600 source.conf "$TARGET_PATH"

# Layer 4: Post-creation verification
check_not_symlink "$TARGET_PATH"
```

**Why multiple layers?**
- Pre-flight checks catch obvious attacks
- Atomic operations minimize race windows
- Post-creation verification catches race condition exploits
- Checking parent directories prevents indirect attacks

### Testing

Run symlink protection tests:
```bash
./tests/test_symlink_protection.sh
```

This test demonstrates:
- How `install -m` replaces symlinks (secure for files)
- How `install -d` follows symlinks (requires pre-flight checks)
- How `rm + cp` pattern is vulnerable to race conditions

---

## TOCTOU Race Condition Mitigation

### Problem: [CWE-362](https://cwe.mitre.org/data/definitions/362.html) - Race Condition

Time-of-Check-Time-of-Use (TOCTOU) vulnerabilities occur when there's a gap between checking a condition and using the result. An attacker can change the state during this gap.

### Vulnerable Pattern ❌

```bash
# BAD: Check and use are separate
if [[ ! -e /etc/app/config.conf ]]; then
    # Gap here! Attacker can create symlink
    cp source.conf /etc/app/config.conf
fi

# BAD: Remove then create (large TOCTOU window)
rm -f /etc/app/data.txt
# Attacker recreates as symlink here
echo "data" > /etc/app/data.txt
```

### Secure Pattern ✅

```bash
# GOOD: Atomic operation (no gap between check and use)
install -m 600 source.conf /etc/app/config.conf

# GOOD: Use atomic file creation with umask
(umask 077 && touch /etc/app/lockfile)

# GOOD: Atomic directory creation for lock mechanisms
if ! mkdir /var/lock/myapp.lock 2>/dev/null; then
    log_err "Lock exists, another instance running"
    exit 1
fi
```

### Key Principles

1. **Minimize the gap**: Use atomic operations when possible
2. **Accept races exist**: Add verification layers for critical operations
3. **Fail securely**: If atomicity isn't possible, verify post-operation
4. **Document TOCTOU risks**: Comment where races are unavoidable

---

## File Permission Hardening

### Problem: [CWE-732](https://cwe.mitre.org/data/definitions/732.html) - Incorrect Permission Assignment

Sensitive files must have restrictive permissions from creation. Default permissions may be too permissive.

### Vulnerable Pattern ❌

```bash
# BAD: File created with default permissions first
touch /etc/app/secrets.conf
# Window where file is world-readable!
chmod 600 /etc/app/secrets.conf

# BAD: Default umask may be permissive
echo "api_key=secret" > /etc/app/api.conf
```

### Secure Pattern ✅

```bash
# GOOD: Set permissions atomically during creation
install -m 600 /dev/null /etc/app/secrets.conf

# GOOD: Set restrictive umask before creation
(umask 077 && touch /etc/app/lockfile)

# GOOD: Specify permissions in install command
install -d -m 700 /etc/app/private
install -m 600 source.conf /etc/app/private/config.conf
```

### Standard Permissions

| File Type | Permission | Octal | Use Case |
|-----------|-----------|-------|----------|
| Private config | `rw-------` | 600 | Configuration with secrets |
| Private directory | `rwx------` | 700 | Directory with sensitive files |
| Shared config | `rw-r--r--` | 644 | Configuration without secrets |
| Executable | `rwxr-xr-x` | 755 | Scripts, binaries |
| Secure executable | `rwx------` | 700 | Scripts with embedded secrets |

---

## Command Injection Prevention

### Problem: [CWE-78](https://cwe.mitre.org/data/definitions/78.html) - OS Command Injection

Occurs when untrusted input is used to construct shell commands without proper sanitization.

### Vulnerable Pattern ❌

```bash
# BAD: Variable interpolation in eval or bash -c
hours="$USER_INPUT"
bash -c "find /var/log -mtime -${hours} -type f"

# BAD: Unquoted variables in commands
filename=$1
cat $filename  # If filename="file1.txt file2.txt", expands to two args
```

### Secure Pattern ✅

```bash
# GOOD: Validate input before use
if [[ ! "$hours" =~ ^[0-9]+$ ]]; then
    log_err "Invalid input: must be numeric"
    exit 1
fi
find /var/log -mtime -"${hours}" -type f

# GOOD: Always quote variables
filename="$1"
cat "$filename"

# GOOD: Use arrays for complex arguments
args=(-type f -name "*.log" -mtime -7)
find /var/log "${args[@]}"
```

### Key Principles

1. **Validate input**: Use regex to ensure input matches expected format
2. **Quote everything**: Always quote variables: `"$var"`
3. **Avoid eval**: Never use `eval` with untrusted input
4. **Use arrays**: For complex command construction, use bash arrays

---

## Path Traversal Protection

### Problem: [CWE-22](https://cwe.mitre.org/data/definitions/22.html) - Path Traversal

Occurs when user input is used to construct file paths without validation, allowing access outside intended directories.

### Vulnerable Pattern ❌

```bash
# BAD: Direct path concatenation
user_file="$1"
cat "/var/data/$user_file"  # Could be "../../etc/passwd"

# BAD: No validation of path components
restore_path="$USER_INPUT"
tar -xzf backup.tar.gz -C "$restore_path"
```

### Secure Pattern ✅

```bash
# GOOD: Validate no traversal sequences
validate_path() {
    local path="$1"
    if [[ "$path" =~ \.\. ]]; then
        log_err "Path traversal detected: $path"
        return 1
    fi
    if [[ "$path" = /* ]]; then
        log_err "Absolute path not allowed: $path"
        return 1
    fi
    return 0
}

# GOOD: Canonicalize and verify path is within expected root
user_file="$1"
validate_path "$user_file" || exit 1
full_path="$(cd /var/data && realpath "$user_file")"
if [[ "$full_path" != /var/data/* ]]; then
    log_err "Path outside allowed directory"
    exit 1
fi
```

### Key Principles

1. **Reject `..` sequences**: Simple check for most cases
2. **Canonicalize paths**: Use `realpath` or `readlink -f`
3. **Verify prefix**: Ensure resolved path is within expected root
4. **Reject absolute paths**: Unless explicitly expected

---

## Credential Security

### Problem: [CWE-214](https://cwe.mitre.org/data/definitions/214.html) - Information Exposure Through Process Environment

Credentials passed as command-line arguments are visible in process listings (`ps`, `/proc`).

### Vulnerable Pattern ❌

```bash
# BAD: Credentials visible in process list
rclone mount remote: /mnt/remote --user admin --pass secret123

# BAD: Credentials in command history
mysql -u admin -p'secret123' mydb
```

### Secure Pattern ✅

```bash
# GOOD: Credentials via environment variables
export RCLONE_USER="admin"
export RCLONE_PASS="secret123"
rclone mount remote: /mnt/remote

# GOOD: Credentials from secure storage
api_key="$(op read "op://vault/item/field")"

# GOOD: Credentials from restricted file
chmod 600 /etc/app/secrets.env
source /etc/app/secrets.env
```

### Key Principles

1. **Use environment variables**: Not visible in `ps` output
2. **Use secret management**: 1Password, HashiCorp Vault, etc.
3. **Avoid command-line args**: Never pass secrets via CLI flags
4. **Restrict config files**: Ensure secret files are mode 600
5. **Mask in logs**: Use `::add-mask::` in GitHub Actions

---

## Quick Reference Checklist

When writing or reviewing security-sensitive code:

**File Operations**
- [ ] Use `install -m 600` instead of `rm + cp + chmod`
- [ ] Use `install -d -m 700` for directories (with pre-flight checks)
- [ ] Add pre-flight symlink checks for critical paths
- [ ] Add post-creation verification for defense-in-depth
- [ ] Check parent directories aren't symlinks

**Permissions**
- [ ] Use restrictive permissions (600/700) for sensitive files/dirs
- [ ] Set permissions atomically during creation
- [ ] Never rely on default umask for security

**Input Validation**
- [ ] Validate numeric inputs with regex: `[[ "$var" =~ ^[0-9]+$ ]]`
- [ ] Reject path traversal: Check for `..` sequences
- [ ] Validate paths are within expected root
- [ ] Quote all variables: `"$var"`

**Credentials**
- [ ] Use environment variables, not CLI args
- [ ] Source from secure storage (1Password, etc.)
- [ ] Ensure secret files are mode 600
- [ ] Mask secrets in logs and CI output

**Race Conditions**
- [ ] Use atomic operations when possible
- [ ] Document unavoidable TOCTOU risks
- [ ] Add verification layers for critical operations

---

## Testing Your Code

### Run Security Tests

```bash
# Symlink protection tests
./tests/test_symlink_protection.sh

# Path validation tests
python3 ./tests/test_path_validation.py

# SSH configuration security
./tests/test_ssh_config.sh
```

### Manual Security Review

1. Search for vulnerable patterns:
   ```bash
   # Find rm + cp patterns
   grep -r "rm.*cp" scripts/
   
   # Find chmod after file creation
   grep -r "touch.*chmod" scripts/
   
   # Find eval usage
   grep -r "eval\|bash -c" scripts/
   ```

2. Check file permissions:
   ```bash
   # Find world-readable config files
   find . -name "*.conf" -perm -004
   ```

3. Review command-line argument handling:
   ```bash
   # Look for potential command injection
   grep -r 'bash -c.*\$' scripts/
   ```

---

## References

- [CWE-22: Path Traversal](https://cwe.mitre.org/data/definitions/22.html)
- [CWE-59: Improper Link Resolution Before File Access](https://cwe.mitre.org/data/definitions/59.html)
- [CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html)
- [CWE-88: Argument Injection](https://cwe.mitre.org/data/definitions/88.html)
- [CWE-214: Information Exposure Through Process Environment](https://cwe.mitre.org/data/definitions/214.html)
- [CWE-362: Race Condition (TOCTOU)](https://cwe.mitre.org/data/definitions/362.html)
- [CWE-732: Incorrect Permission Assignment](https://cwe.mitre.org/data/definitions/732.html)

## Additional Resources

- Internal Security Journal: `.jules/sentinel.md` - Documents all security vulnerabilities found and fixed
- Security Audit: `SECURITY_AUDIT.md` - Repository-wide security assessment
- Security Incident Response: `SECURITY_INCIDENT_RESPONSE.md` - Incident handling procedures

---

*This document is a living guide. When you discover new security patterns or vulnerabilities, please update both this document and the sentinel journal (`.jules/sentinel.md`).*
