# Shared Libraries

This directory contains reusable shell script libraries that provide common functionality across the personal-config repository.

## 📚 Available Libraries

### [`logging.sh`](logging.sh)

**Purpose**: Centralized logging and error handling for shell scripts.

**Features**:
- Color-coded logging (INFO, OK, WARN, ERROR, DEBUG)
- Standard error handling with line numbers
- Signal trapping for graceful exits
- Configuration validation functions
- Utility functions for common operations

**Usage**:
```bash
#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/lib/logging.sh"

# Initialize script
init_script "my_script.sh" "My awesome script"

# Use logging functions
log_info "Starting operation..."
log_ok "Operation completed successfully"
log_warn "Something might be wrong"
log_err "Something went wrong"

# Use validation functions
require_cmd "git" "Install git with: brew install git"
require_file "/etc/hosts" "Hosts file"
require_dir "/tmp" "Temporary directory"

# Use utility functions
get_abs_path "/some/path"
get_repo_root
```

### [`utils.sh`](utils.sh)

**Purpose**: Common utility functions for file operations, string manipulation, and system interactions.

**Features**:
- File and directory operations
- String manipulation functions
- Array operations
- System information gathering
- Network utilities
- Git utilities
- Process management
- Time and date utilities
- File permission utilities
- Symlink management

**Usage**:
```bash
#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/lib/logging.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/lib/utils.sh"

# File operations
files=($(find_files "*.sh" "scripts/"))
count=$(count_lines "myfile.txt")

# String manipulation
lower=$(to_lowercase "HELLO")
trimmed=$(trim "  hello  ")

# System information
if is_ci; then
    log_info "Running in CI environment"
fi

# Git operations
branch=$(get_git_branch)
if is_git_clean; then
    log_ok "Repository is clean"
fi

# Symlink management
create_symlink "source/file" "target/link"
verify_symlink "target/link" "expected/source"
```

## 🚀 Quick Start

### For New Scripts

Add this at the top of your shell scripts:

```bash
#!/usr/bin/env bash

# Source the shared libraries
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load logging library (required)
source "$REPO_ROOT/scripts/lib/logging.sh"

# Load utils library (optional, but recommended)
source "$REPO_ROOT/scripts/lib/utils.sh"

# Initialize script
init_script "$(basename "$0")" "Description of what this script does"

# Your code here
main() {
    log_info "Starting main function"
    # ... your code
    log_ok "Script completed successfully"
}

# Run main with error handling
run_main "$@"
```

### For Existing Scripts

Gradually migrate your existing scripts to use these libraries:

1. **Start with error handling**: Add `set -Eeuo pipefail` and the error trapping from `logging.sh`
2. **Replace echo statements**: Use `log_info`, `log_ok`, `log_warn`, `log_err` instead of `echo`
3. **Use utility functions**: Replace common code patterns with functions from `utils.sh`
4. **Add validation**: Use `require_cmd`, `require_file`, `require_dir` for input validation

## 🎯 Best Practices

### 1. Always Source Logging First

The `logging.sh` library should be sourced before `utils.sh` because `utils.sh` depends on the logging functions.

```bash
# ✅ Correct
source "$REPO_ROOT/scripts/lib/logging.sh"
source "$REPO_ROOT/scripts/lib/utils.sh"

# ❌ Incorrect
source "$REPO_ROOT/scripts/lib/utils.sh"
source "$REPO_ROOT/scripts/lib/logging.sh"
```

### 2. Use Absolute Paths

Always use absolute paths when sourcing the libraries to avoid issues with relative paths.

```bash
# ✅ Correct
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$REPO_ROOT/scripts/lib/logging.sh"

# ❌ Incorrect (relative path issues)
source "../scripts/lib/logging.sh"
```

### 3. Initialize Scripts Properly

Always call `init_script` at the start of your script to set up error handling and logging.

```bash
init_script "script_name" "Description"
```

### 4. Use run_main for Main Function

Use the `run_main` helper to execute your main function with proper error handling.

```bash
main() {
    # Your code here
}

run_main "$@"
```

### 5. Validate Inputs

Always validate required commands, files, and directories at the start of your functions.

```bash
my_function() {
    require_cmd "git"
    require_file "$CONFIG_FILE" "Configuration file"
    require_dir "$DATA_DIR" "Data directory"
    
    # Rest of your function
}
```

## 📝 Function Reference

### Logging Functions (logging.sh)

| Function | Description | Example |
|----------|-------------|---------|
| `log_info` | Log informational message | `log_info "Starting backup..."` |
| `log_ok` | Log success message | `log_ok "Backup completed"` |
| `log_warn` | Log warning message | `log_warn "Disk space low"` |
| `log_err` | Log error message | `log_err "Operation failed"` |
| `log_debug` | Log debug message (only if DEBUG=1) | `log_debug "Variable value: $var"` |
| `log_header` | Log section header | `log_header "Configuration"` |
| `log_hr` | Log horizontal rule | `log_hr` |

### Validation Functions (logging.sh)

| Function | Description | Example |
|----------|-------------|---------|
| `require_cmd` | Check if command exists | `require_cmd "git" "Install git"` |
| `require_file` | Check if file exists and is readable | `require_file "/etc/hosts"` |
| `require_dir` | Check if directory exists | `require_dir "/tmp"` |
| `require_var` | Check if variable is set | `require_var "API_KEY"` |
| `ensure_macos` | Check if running on macOS | `ensure_macos` |
| `ensure_not_root` | Check if not running as root | `ensure_not_root` |

### Utility Functions (utils.sh)

#### File Operations
| Function | Description | Example |
|----------|-------------|---------|
| `find_files` | Find files by pattern | `find_files "*.sh" "scripts/"` |
| `find_shell_scripts` | Find all shell scripts | `find_shell_scripts` |
| `find_python_files` | Find all Python files | `find_python_files` |
| `file_contains` | Check if file contains pattern | `file_contains "file.txt" "pattern"` |
| `count_lines` | Count lines in file | `count_lines "file.txt"` |
| `get_file_size` | Get file size in bytes | `get_file_size "file.txt"` |

#### String Operations
| Function | Description | Example |
|----------|-------------|---------|
| `to_lowercase` | Convert to lowercase | `to_lowercase "HELLO"` |
| `to_uppercase` | Convert to uppercase | `to_uppercase "hello"` |
| `trim` | Trim whitespace | `trim "  hello  "` |
| `starts_with` | Check if string starts with prefix | `starts_with "hello" "he"` |
| `ends_with` | Check if string ends with suffix | `ends_with "hello" "lo"` |
| `contains` | Check if string contains substring | `contains "hello" "ell"` |
| `replace_all` | Replace all occurrences | `replace_all "hello" "l" "x"` |

#### System Information
| Function | Description | Example |
|----------|-------------|---------|
| `get_current_user` | Get current user | `get_current_user` |
| `get_hostname` | Get hostname | `get_hostname` |
| `get_os` | Get OS name | `get_os` |
| `is_ci` | Check if in CI environment | `is_ci` |
| `is_docker` | Check if in Docker | `is_docker` |
| `get_cpu_count` | Get CPU count | `get_cpu_count` |
| `get_total_memory` | Get total memory in MB | `get_total_memory` |

#### Network Utilities
| Function | Description | Example |
|----------|-------------|---------|
| `is_reachable` | Check if host is reachable | `is_reachable "google.com"` |
| `is_internet_available` | Check internet connectivity | `is_internet_available` |
| `get_public_ip` | Get public IP address | `get_public_ip` |

#### Git Utilities
| Function | Description | Example |
|----------|-------------|---------|
| `get_git_branch` | Get current branch | `get_git_branch` |
| `get_git_commit` | Get current commit hash | `get_git_commit` |
| `is_git_clean` | Check if repo is clean | `is_git_clean` |
| `get_git_root` | Get git root directory | `get_git_root` |
| `is_git_repo` | Check if in git repo | `is_git_repo` |

#### Symlink Management
| Function | Description | Example |
|----------|-------------|---------|
| `create_symlink` | Create symlink with backup | `create_symlink "source" "target"` |
| `verify_symlink` | Verify symlink points to expected source | `verify_symlink "target" "expected"` |

## 🔧 Testing the Libraries

You can test the libraries by running:

```bash
# Test logging functions
bash -c "
source scripts/lib/logging.sh
init_script 'test' 'Testing logging library'
log_info 'Test info message'
log_ok 'Test success message'
log_warn 'Test warning message'
log_err 'Test error message'
DEBUG=1 log_debug 'Test debug message'
"

# Test utility functions
bash -c "
source scripts/lib/logging.sh
source scripts/lib/utils.sh

echo 'Current user:' $(get_current_user)
echo 'Hostname:' $(get_hostname)
echo 'OS:' $(get_os)
echo 'Is CI:' $(is_ci && echo 'Yes' || echo 'No')
echo 'CPU count:' $(get_cpu_count)
echo 'Total memory:' $(get_total_memory) MB
"
```

## 📊 Performance Considerations

- The libraries add minimal overhead to your scripts
- All functions are designed to be fast and efficient
- Debug logging is disabled by default (enable with `DEBUG=1`)
- Error handling adds a small overhead but provides better debugging

## 🔒 Security Considerations

- All functions validate their inputs
- Error handling prevents silent failures
- File operations check permissions before acting
- Network operations have timeouts to prevent hanging

## 📝 Contributing

When adding new functions to these libraries:

1. **Follow the existing patterns** for function naming and structure
2. **Add comprehensive documentation** in the function comments
3. **Include examples** in the function comments
4. **Test thoroughly** before committing
5. **Update this README** with new functions

## 🎉 Migration Guide

### Step 1: Update Existing Scripts

For each existing script, add the library imports at the top:

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

# Add these lines
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$REPO_ROOT/scripts/lib/logging.sh"
source "$REPO_ROOT/scripts/lib/utils.sh"

init_script "$(basename "$0")" "Script description"
```

### Step 2: Replace Common Patterns

**Before**:
```bash
echo "Starting..."
if ! command -v git >/dev/null; then
    echo "Error: git not found" >&2
    exit 1
fi
```

**After**:
```bash
log_info "Starting..."
require_cmd "git" "Install git with: brew install git"
```

### Step 3: Add Error Handling

**Before**:
```bash
#!/usr/bin/env bash
# No error handling
```

**After**:
```bash
#!/usr/bin/env bash
set -Eeuo pipefail
source "$REPO_ROOT/scripts/lib/logging.sh"
setup_error_handling
```

## 🚨 Troubleshooting

### "Command not found" when sourcing libraries

**Problem**: You get `command not found` errors when trying to source the libraries.

**Solution**: Make sure you're using the correct path to the libraries. Use absolute paths:

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$REPO_ROOT/scripts/lib/logging.sh"
```

### Colors not working

**Problem**: Colors don't appear in the output.

**Solution**: 
1. Make sure you're running in a terminal that supports colors
2. Check if `NO_COLOR` environment variable is set
3. Try running with `FORCE_COLOR=1`

### Debug messages not showing

**Problem**: Debug messages don't appear.

**Solution**: Set the `DEBUG` environment variable:

```bash
DEBUG=1 ./your_script.sh
```

## 📞 Support

If you have questions or issues with these libraries, please:

1. Check this README for answers
2. Look at existing scripts that use the libraries
3. Open an issue in the repository

---

**Last Updated**: 2025-01-08  
**Version**: 1.0.0  
**Maintainer**: Repository Owner