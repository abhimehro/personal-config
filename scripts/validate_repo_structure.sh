#!/usr/bin/env bash
#
# Repository Structure Validation Script
# 
# This script validates the repository structure, checks for common issues,
# and provides recommendations for improvements.
#
# Usage: ./scripts/validate_repo_structure.sh [--fix] [--verbose]
#

set -Eeuo pipefail

# Source the shared libraries
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load libraries
if [[ -f "$REPO_ROOT/scripts/lib/logging.sh" ]]; then
    source "$REPO_ROOT/scripts/lib/logging.sh"
else
    echo "Error: logging.sh not found. Please run from repository root." >&2
    exit 1
fi

if [[ -f "$REPO_ROOT/scripts/lib/utils.sh" ]]; then
    source "$REPO_ROOT/scripts/lib/utils.sh"
fi

# Initialize script
init_script "validate_repo_structure.sh" "Repository structure validation and optimization"

# =============================================================================
# GLOBAL VARIABLES
# =============================================================================

FIX_MODE=false
VERBOSE_MODE=false
ISSUES_FOUND=0
FIXES_APPLIED=0

# =============================================================================
# COMMAND LINE ARGUMENTS
# =============================================================================

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --fix|-f)
            FIX_MODE=true
            log_info "Fix mode enabled - will attempt to fix issues"
            shift
            ;;
        --verbose|-v)
            VERBOSE_MODE=true
            DEBUG=1
            log_info "Verbose mode enabled"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--fix] [--verbose]"
            echo ""
            echo "Options:"
            echo "  --fix, -f       Attempt to fix found issues"
            echo "  --verbose, -v   Enable verbose output"
            echo "  --help, -h      Show this help message"
            echo ""
            echo "This script validates the repository structure and checks for:"
            echo "  - Shell script best practices"
            echo "  - File permissions"
            echo "  - Symlink integrity"
            echo "  - Configuration file validity"
            echo "  - Security issues"
            exit 0
            ;;
        *)
            log_err "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

# Validate shell scripts
validate_shell_scripts() {
    log_header "Shell Script Validation"
    
    local scripts_found=0
    local scripts_with_issues=0
    local scripts_without_error_handling=0
    local scripts_without_shebang=0
    
    # Find all shell scripts
    local scripts
    scripts=$(find_shell_scripts "$REPO_ROOT")
    
    while IFS= read -r script; do
        scripts_found=$((scripts_found + 1))
        
        # Skip scripts in .git directory
        if [[ "$script" == *".git"* ]]; then
            continue
        fi
        
        # Check for shebang
        local first_line
        first_line=$(head -1 "$script")
        if ! starts_with "$first_line" "#!"; then
            log_warn "Script missing shebang: $script"
            scripts_without_shebang=$((scripts_without_shebang + 1))
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
        
        # Check for error handling
        if ! file_contains "$script" "set -e" && ! file_contains "$script" "set -E" && \
           ! file_contains "$script" "set -u" && ! file_contains "$script" "set -o pipefail"; then
            log_warn "Script missing error handling: $script"
            scripts_without_error_handling=$((scripts_without_error_handling + 1))
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
        
        # Check for sourcing the logging library (optional check)
        if ! file_contains "$script" "scripts/lib/logging.sh" && \
           ! file_contains "$script" "source.*logging"; then
            if [[ "$VERBOSE_MODE" == true ]]; then
                log_debug "Script not using shared logging library: $script"
            fi
        fi
        
    done <<< "$scripts"
    
    log_info "Validated $scripts_found shell scripts"
    log_info "  - Missing shebang: $scripts_without_shebang"
    log_info "  - Missing error handling: $scripts_without_error_handling"
    
    if [[ $scripts_without_shebang -gt 0 || $scripts_without_error_handling -gt 0 ]]; then
        log_warn "Shell script validation found issues"
    else
        log_ok "Shell script validation passed"
    fi
}

# Validate file permissions
validate_file_permissions() {
    log_header "File Permissions Validation"
    
    local files_with_issues=0
    
    # Check for executable scripts without execute permission
    local scripts
    scripts=$(find_shell_scripts "$REPO_ROOT")
    
    while IFS= read -r script; do
        # Skip scripts in .git directory
        if [[ "$script" == *".git"* ]]; then
            continue
        fi
        
        # Check if script has execute permission
        if ! is_executable "$script"; then
            log_warn "Script not executable: $script"
            files_with_issues=$((files_with_issues + 1))
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
            
            if [[ "$FIX_MODE" == true ]]; then
                chmod +x "$script"
                log_info "Fixed permissions for: $script"
                FIXES_APPLIED=$((FIXES_APPLIED + 1))
            fi
        fi
        
    done <<< "$scripts"
    
    # Check for sensitive files with wrong permissions
    local sensitive_files=(
        ".env*"
        "*.key"
        "*.pem"
        "*.p12"
        "*.pfx"
        "*.crt"
        "config.json"
        "secrets*"
    )
    
    for pattern in "${sensitive_files[@]}"; do
        local files
        files=$(find "$REPO_ROOT" -name "$pattern" -type f 2>/dev/null)
        
        while IFS= read -r file; do
            # Skip .git directory
            if [[ "$file" == *".git"* ]]; then
                continue
            fi
            
            # Check if file is world-readable
            if [[ -r "$file" ]] && [[ "$(stat -c "%a" "$file" 2>/dev/null || stat -f "%OLp" "$file" 2>/dev/null)" == *"7"* || "$(stat -c "%a" "$file" 2>/dev/null || stat -f "%OLp" "$file" 2>/dev/null)" == *"6"* ]]; then
                # Check if it's in .gitignore
                if ! grep -q "$(basename "$file")" "$REPO_ROOT/.gitignore" 2>/dev/null; then
                    log_warn "Sensitive file might be committed: $file"
                    files_with_issues=$((files_with_issues + 1))
                    ISSUES_FOUND=$((ISSUES_FOUND + 1))
                fi
            fi
            
        done <<< "$files"
    done
    
    if [[ $files_with_issues -eq 0 ]]; then
        log_ok "File permissions validation passed"
    else
        log_warn "File permissions validation found issues"
    fi
}

# Validate symlinks
validate_symlinks() {
    log_header "Symlink Validation"
    
    local symlinks_found=0
    local broken_symlinks=0
    
    # Find all symlinks in the repository
    local symlinks
    symlinks=$(find "$REPO_ROOT" -type l 2>/dev/null)
    
    while IFS= read -r symlink; do
        symlinks_found=$((symlinks_found + 1))
        
        # Skip .git directory
        if [[ "$symlink" == *".git"* ]]; then
            continue
        fi
        
        # Check if symlink target exists
        if [[ ! -e "$symlink" ]]; then
            log_warn "Broken symlink: $symlink"
            broken_symlinks=$((broken_symlinks + 1))
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
            
            if [[ "$FIX_MODE" == true ]]; then
                local target
                target=$(readlink "$symlink")
                log_info "Attempting to fix broken symlink: $symlink -> $target"
                
                # Try to recreate the symlink
                if [[ -e "$target" ]]; then
                    rm -f "$symlink"
                    ln -s "$target" "$symlink"
                    log_info "Fixed symlink: $symlink"
                    FIXES_APPLIED=$((FIXES_APPLIED + 1))
                else
                    log_warn "Cannot fix symlink - target does not exist: $target"
                fi
            fi
        fi
        
    done <<< "$symlinks"
    
    log_info "Validated $symlinks_found symlinks, $broken_symlinks broken"
    
    if [[ $broken_symlinks -eq 0 ]]; then
        log_ok "Symlink validation passed"
    else
        log_warn "Symlink validation found issues"
    fi
}

# Validate JSON files
validate_json_files() {
    log_header "JSON Validation"
    
    local json_files_found=0
    local invalid_json_files=0
    
    # Find all JSON files
    local json_files
    json_files=$(find "$REPO_ROOT" -name "*.json" -type f 2>/dev/null)
    
    while IFS= read -r json_file; do
        json_files_found=$((json_files_found + 1))
        
        # Skip .git directory
        if [[ "$json_file" == *".git"* ]]; then
            continue
        fi
        
        # Skip node_modules
        if [[ "$json_file" == *"node_modules"* ]]; then
            continue
        fi
        
        # Validate JSON
        if ! jq empty "$json_file" 2>/dev/null; then
            log_warn "Invalid JSON: $json_file"
            invalid_json_files=$((invalid_json_files + 1))
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
        
    done <<< "$json_files"
    
    log_info "Validated $json_files_found JSON files, $invalid_json_files invalid"
    
    if [[ $invalid_json_files -eq 0 ]]; then
        log_ok "JSON validation passed"
    else
        log_warn "JSON validation found issues"
    fi
}

# Validate YAML files
validate_yaml_files() {
    log_header "YAML Validation"
    
    local yaml_files_found=0
    local invalid_yaml_files=0
    
    # Find all YAML files
    local yaml_files
    yaml_files=$(find "$REPO_ROOT" -name "*.yaml" -o -name "*.yml" | grep -v ".git" 2>/dev/null)
    
    while IFS= read -r yaml_file; do
        yaml_files_found=$((yaml_files_found + 1))
        
        # Skip .git directory
        if [[ "$yaml_file" == *".git"* ]]; then
            continue
        fi
        
        # Skip node_modules
        if [[ "$yaml_file" == *"node_modules"* ]]; then
            continue
        fi
        
        # Validate YAML (basic check)
        if ! python3 -c "import yaml; yaml.safe_load(open('$yaml_file'))" 2>/dev/null; then
            log_warn "Invalid YAML: $yaml_file"
            invalid_yaml_files=$((invalid_yaml_files + 1))
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
        
    done <<< "$yaml_files"
    
    log_info "Validated $yaml_files_found YAML files, $invalid_yaml_files invalid"
    
    if [[ $invalid_yaml_files -eq 0 ]]; then
        log_ok "YAML validation passed"
    else
        log_warn "YAML validation found issues"
    fi
}

# Check for large files
check_large_files() {
    log_header "Large Files Check"
    
    local large_files_found=0
    local MAX_FILE_SIZE=$((10 * 1024 * 1024))  # 10MB
    
    # Find large files (excluding .git)
    local large_files
    large_files=$(find "$REPO_ROOT" -type f -size +${MAX_FILE_SIZE}c -not -path "*\.git*" 2>/dev/null)
    
    while IFS= read -r file; do
        local file_size
        file_size=$(get_file_size "$file")
        local file_size_mb
        file_size_mb=$((file_size / 1024 / 1024))
        
        log_warn "Large file found: $file (${file_size_mb}MB)"
        large_files_found=$((large_files_found + 1))
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
        
    done <<< "$large_files"
    
    if [[ $large_files_found -eq 0 ]]; then
        log_ok "No large files found (max ${MAX_FILE_SIZE} bytes)"
    else
        log_warn "Large files check found issues"
    fi
}

# Check for duplicate files
check_duplicate_files() {
    log_header "Duplicate Files Check"
    
    local duplicates_found=0
    
    # Find potential duplicates by checking for files with same content
    # This is a simple check and might have false positives
    local files
    files=$(find "$REPO_ROOT" -type f -not -path "*\.git*" -not -path "*node_modules*" 2>/dev/null)
    
    # Use a temporary directory for checksums
    local tmp_dir
    tmp_dir=$(mktemp -d)
    trap "rm -rf $tmp_dir" EXIT
    
    while IFS= read -r file; do
        # Skip binary files
        if file "$file" | grep -q "binary"; then
            continue
        fi
        
        # Get file size
        local file_size
        file_size=$(get_file_size "$file")
        
        # Skip very small files
        if [[ $file_size -lt 10 ]]; then
            continue
        fi
        
        # Calculate checksum
        local checksum
        checksum=$(md5sum "$file" | awk '{print $1}')
        local checksum_file="$tmp_dir/$checksum"
        
        if [[ -f "$checksum_file" ]]; then
            local existing_files
            existing_files=$(cat "$checksum_file")
            
            # Check if this file is already in the list
            if ! grep -q "$file" "$checksum_file"; then
                log_warn "Potential duplicate: $file (same as: $existing_files)"
                duplicates_found=$((duplicates_found + 1))
                ISSUES_FOUND=$((ISSUES_FOUND + 1))
                echo "$existing_files" >> "$checksum_file"
            fi
            echo "$file" >> "$checksum_file"
        else
            echo "$file" > "$checksum_file"
        fi
        
    done <<< "$files"
    
    if [[ $duplicates_found -eq 0 ]]; then
        log_ok "No duplicate files found"
    else
        log_warn "Duplicate files check found potential issues"
    fi
}

# Check for security issues
check_security_issues() {
    log_header "Security Check"
    
    local security_issues=0
    
    # Check for hardcoded passwords
    local password_patterns=(
        "password[\-_:=]".*[^\s]+
        "passwd[\-_:=]".*[^\s]+
        "pwd[\-_:=]".*[^\s]+
        "secret[\-_:=]".*[^\s]+
        "api[\-_:=]?key[\-_:=]".*[^\s]+
        "token[\-_:=]".*[^\s]+
    )
    
    for pattern in "${password_patterns[@]}"; do
        local files_with_patterns
        files_with_patterns=$(grep -r --include="*.sh" --include="*.py" --include="*.json" --include="*.yaml" --include="*.yml" -l "$pattern" "$REPO_ROOT" 2>/dev/null || true)
        
        while IFS= read -r file; do
            # Skip .git directory
            if [[ "$file" == *".git"* ]]; then
                continue
            fi
            
            # Skip test files
            if [[ "$file" == *"test"* ]] || [[ "$file" == *"mock"* ]] || [[ "$file" == *"example"* ]]; then
                continue
            fi
            
            log_warn "Potential hardcoded secret in: $file"
            security_issues=$((security_issues + 1))
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
            
        done <<< "$files_with_patterns"
    done
    
    # Check for files that should be in .gitignore
    local sensitive_extensions=(
        ".env"
        ".key"
        ".pem"
        ".p12"
        ".pfx"
        ".crt"
        ".pem"
        "id_rsa"
        "id_dsa"
        "id_ed25519"
        "id_ecdsa"
    )
    
    for ext in "${sensitive_extensions[@]}"; do
        local sensitive_files
        sensitive_files=$(find "$REPO_ROOT" -name "*$ext*" -type f 2>/dev/null)
        
        while IFS= read -r file; do
            # Skip .git directory
            if [[ "$file" == *".git"* ]]; then
                continue
            fi
            
            # Check if file is tracked by git
            if git ls-files "$file" 2>/dev/null | grep -q "$file"; then
                log_warn "Sensitive file is tracked by git: $file"
                security_issues=$((security_issues + 1))
                ISSUES_FOUND=$((ISSUES_FOUND + 1))
            fi
            
        done <<< "$sensitive_files"
    done
    
    if [[ $security_issues -eq 0 ]]; then
        log_ok "Security check passed"
    else
        log_warn "Security check found issues"
    fi
}

# =============================================================================
# MAIN VALIDATION FUNCTION
# =============================================================================

run_validation() {
    log_header "Repository Structure Validation"
    log_info "Starting validation of: $REPO_ROOT"
    log_info "Fix mode: $FIX_MODE"
    log_info "Verbose mode: $VERBOSE_MODE"
    echo
    
    # Run all validation checks
    validate_shell_scripts
    echo
    
    validate_file_permissions
    echo
    
    validate_symlinks
    echo
    
    validate_json_files
    echo
    
    validate_yaml_files
    echo
    
    check_large_files
    echo
    
    check_duplicate_files
    echo
    
    check_security_issues
    echo
    
    # Summary
    log_header "Validation Summary"
    log_info "Total issues found: $ISSUES_FOUND"
    log_info "Fixes applied: $FIXES_APPLIED"
    
    if [[ $ISSUES_FOUND -eq 0 ]]; then
        log_ok "✅ All validation checks passed!"
        return 0
    else
        log_warn "⚠️  $ISSUES_FOUND issues found"
        if [[ "$FIX_MODE" == true ]]; then
            log_info "$FIXES_APPLIED issues were automatically fixed"
        else
            log_info "Run with --fix to attempt automatic fixes"
        fi
        return 1
    fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    # Check if we're in the repository root
    if [[ ! -f "$REPO_ROOT/setup.sh" ]]; then
        log_err "This script must be run from the repository root or scripts directory"
        exit 1
    fi
    
    # Run validation
    run_validation
}

# Run main function
run_main "$@"