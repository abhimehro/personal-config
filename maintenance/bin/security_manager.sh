#!/usr/bin/env bash

# Advanced Security & Backup Management System
# Provides configuration backup, security monitoring, and recovery mechanisms
set -eo pipefail

# Configuration
LOG_DIR="$HOME/Library/Logs/maintenance"
BACKUP_DIR="$HOME/Library/Logs/maintenance/backups"
SECURITY_LOG="$LOG_DIR/security.log"
CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../" && pwd)"

mkdir -p "$BACKUP_DIR"

# Basic logging
log_security() {
    local ts="$(date '+%Y-%m-%d %H:%M:%S')"
    local level="${1:-INFO}"
    shift
    echo "$ts [SECURITY] [$level] $*" | tee -a "$SECURITY_LOG"
}

# Load smart notification system
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/smart_notifier.sh" ]]; then
    source "$SCRIPT_DIR/smart_notifier.sh"
fi

log_security "INFO" "Security manager initialized"

# Configuration backup functions
backup_config() {
    local backup_type="${1:-incremental}"  # full, incremental
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    log_security "INFO" "Starting $backup_type configuration backup"
    
    local backup_name="config_backup_${backup_type}_${timestamp}"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    mkdir -p "$backup_path"
    
    # Backup maintenance configuration
    log_security "INFO" "Backing up maintenance configuration"
    
    # Config files
    if [[ -d "$CONFIG_DIR/conf" ]]; then
        cp -R "$CONFIG_DIR/conf" "$backup_path/" 2>/dev/null || true
    fi
    
    # Scripts (without logs)
    if [[ -d "$CONFIG_DIR/bin" ]]; then
        mkdir -p "$backup_path/bin"
        find "$CONFIG_DIR/bin" -name "*.sh" -exec cp {} "$backup_path/bin/" \; 2>/dev/null || true
    fi
    
    # Launch agents
    if [[ -d "$CONFIG_DIR/launchd" ]]; then
        cp -R "$CONFIG_DIR/launchd" "$backup_path/" 2>/dev/null || true
    fi
    
    # Documentation
    find "$CONFIG_DIR" -maxdepth 1 -name "*.md" -exec cp {} "$backup_path/" \; 2>/dev/null || true
    
    # System preferences and settings
    log_security "INFO" "Backing up system preferences"
    
    mkdir -p "$backup_path/system"
    
    # SSH configuration (excluding private keys for security)
    if [[ -d "$HOME/.ssh" ]]; then
        mkdir -p "$backup_path/system/ssh"
        cp "$HOME/.ssh/config" "$backup_path/system/ssh/" 2>/dev/null || true
        cp "$HOME/.ssh"/*.pub "$backup_path/system/ssh/" 2>/dev/null || true
    fi
    
    # Git configuration
    cp "$HOME/.gitconfig" "$backup_path/system/" 2>/dev/null || true
    cp "$HOME/.gitignore_global" "$backup_path/system/" 2>/dev/null || true
    
    # Shell configurations
    cp "$HOME/.bashrc" "$backup_path/system/" 2>/dev/null || true
    cp "$HOME/.bash_profile" "$backup_path/system/" 2>/dev/null || true
    cp "$HOME/.zshrc" "$backup_path/system/" 2>/dev/null || true
    
    # Fish shell config
    if [[ -d "$HOME/.config/fish" ]]; then
        mkdir -p "$backup_path/system/fish"
        cp -R "$HOME/.config/fish"/* "$backup_path/system/fish/" 2>/dev/null || true
    fi
    
    # Homebrew bundle (if available)
    if command -v brew >/dev/null 2>&1; then
        log_security "INFO" "Creating Homebrew bundle"
        cd "$backup_path" && brew bundle dump 2>/dev/null || true
    fi
    
    # Create backup manifest
    cat > "$backup_path/MANIFEST.txt" << EOF
Backup Manifest
===============
Type: $backup_type
Created: $(date)
System: $(uname -a)
User: $(whoami)
Backup Path: $backup_path

Contents:
- Maintenance configuration (conf/, bin/, launchd/)
- Documentation (*.md files)
- System preferences (SSH config, Git config, Shell configs)
- Homebrew bundle (Brewfile)

Exclusions:
- Log files and temporary data
- Private keys and sensitive credentials
- Large binary files

Restore Instructions:
1. Copy configuration files to appropriate locations
2. Set executable permissions on scripts: chmod +x bin/*.sh
3. Install Homebrew packages: brew bundle install
4. Load launch agents: launchctl load launchd/*.plist
5. Review and customize configurations as needed
EOF
    
    # Compress backup
    local archive_path="$BACKUP_DIR/${backup_name}.tar.gz"
    cd "$BACKUP_DIR" && tar -czf "${backup_name}.tar.gz" "$backup_name" 2>/dev/null
    
    if [[ $? -eq 0 ]]; then
        rm -rf "$backup_path"

        # Generate SHA256 checksum for integrity verification
        if command -v shasum >/dev/null 2>&1; then
            shasum -a 256 "$archive_path" > "${archive_path}.sha256"
            log_security "INFO" "Generated SHA256 checksum for backup integrity"
        elif command -v sha256sum >/dev/null 2>&1; then
            sha256sum "$archive_path" > "${archive_path}.sha256"
            log_security "INFO" "Generated SHA256 checksum for backup integrity"
        else
            log_security "WARN" "Checksum utility not found - skipping integrity hash generation"
        fi

        log_security "INFO" "Backup completed successfully: $archive_path"
        
        # Calculate backup size
        local backup_size=$(du -h "$archive_path" | cut -f1)
        
        # Send notification
        if command -v smart_notify >/dev/null 2>&1; then
            smart_notify "success" "🔒 Configuration Backup" "Backup completed successfully\nSize: $backup_size\nType: $backup_type"
        fi
        
        echo "$archive_path"
    else
        log_security "ERROR" "Backup compression failed"
        return 1
    fi
}

# Security check for backup contents
check_backup_safety() {
    local backup_file="$1"
    local checksum_file="${backup_file}.sha256"

    log_security "INFO" "Verifying backup safety: $backup_file"

    # 1. Check integrity (Checksum)
    local checksum_file="${backup_file}.sha256"
    if [[ -f "$checksum_file" ]]; then
        log_security "INFO" "Verifying backup integrity using SHA256 checksum..."
        if command -v shasum >/dev/null 2>&1; then
        if command -v shasum >/dev/null 2>&1; then
            local expected_hash=$(awk '{print $1}' "$checksum_file")
            if ! echo "$expected_hash  $backup_file" | shasum -a 256 -c - >/dev/null 2>&1; then
                log_security "ERROR" "SECURITY ALERT: Backup checksum verification failed! File may be corrupted or tampered with."
                return 1
            fi
            log_security "INFO" "Integrity check passed (shasum)"
        elif command -v sha256sum >/dev/null 2>&1; then
            local expected_hash=$(awk '{print $1}' "$checksum_file")
            if ! echo "$expected_hash  $backup_file" | sha256sum -c - >/dev/null 2>&1; then
                log_security "ERROR" "SECURITY ALERT: Backup checksum verification failed! File may be corrupted or tampered with."
                return 1
            fi
            log_security "INFO" "Integrity check passed (sha256sum)"
        else
            log_security "WARN" "Checksum file exists but verification tool missing."
        fi
    else
        log_security "ERROR" "SECURITY ALERT: No checksum file found - aborting for safety."
        return 1
    fi

    # 2. Check for unsafe paths (Directory Traversal)
    if tar -tf "$backup_file" 2>/dev/null | grep -qE '(^|/)\.\.(/|$)|^/'; then
        log_security "ERROR" "Security check failed: Backup contains unsafe paths (absolute or relative path traversal)"
        return 1
    fi

    log_security "INFO" "Backup safety check passed"
    return 0
}

# Restore configuration from backup
restore_config() {
    local backup_file="$1"
    local restore_mode="${2:-preview}"  # preview, restore
    
    if [[ ! -f "$backup_file" ]]; then
        log_security "ERROR" "Backup file not found: $backup_file"
        return 1
    fi
    
    log_security "INFO" "Starting configuration restore from $backup_file (mode: $restore_mode)"
    
    local temp_dir=$(mktemp -d)
    local backup_name=$(basename "$backup_file" .tar.gz)
    
    # Verify backup safety before extraction
    if ! check_backup_safety "$backup_file"; then
        log_security "ERROR" "Backup verification failed - aborting restore"
        rm -rf "$temp_dir"
        return 1
    fi

    # Extract backup
    cd "$temp_dir" && tar -xzf "$backup_file" 2>/dev/null
    
    if [[ ! -d "$temp_dir/$backup_name" ]]; then
        log_security "ERROR" "Failed to extract backup or invalid backup structure"
        rm -rf "$temp_dir"
        return 1
    fi
    
    local restore_path="$temp_dir/$backup_name"
    
    # Show manifest
    if [[ -f "$restore_path/MANIFEST.txt" ]]; then
        echo "Backup Manifest:"
        echo "================"
        cat "$restore_path/MANIFEST.txt"
        echo ""
    fi
    
    if [[ "$restore_mode" == "preview" ]]; then
        echo "Preview Mode - Files that would be restored:"
        echo "============================================="
        find "$restore_path" -type f | sed "s|$restore_path||" | head -20
        echo ""
        echo "Run with 'restore' mode to actually restore files"
        log_security "INFO" "Restore preview completed"
    else
        echo "Restore Mode - Restoring configuration files:"
        echo "============================================="
        
        # Restore maintenance configuration
        if [[ -d "$restore_path/conf" ]]; then
            cp -R "$restore_path/conf"/* "$CONFIG_DIR/conf/" 2>/dev/null || true
            echo "✅ Restored maintenance config"
        fi
        
        if [[ -d "$restore_path/bin" ]]; then
            cp -R "$restore_path/bin"/* "$CONFIG_DIR/bin/" 2>/dev/null || true
            chmod +x "$CONFIG_DIR/bin"/*.sh 2>/dev/null || true
            echo "✅ Restored maintenance scripts"
        fi
        
        if [[ -d "$restore_path/launchd" ]]; then
            cp -R "$restore_path/launchd"/* "$CONFIG_DIR/launchd/" 2>/dev/null || true
            echo "✅ Restored launch agents"
        fi
        
        # Restore system configurations (with user confirmation for sensitive files)
        echo ""
        echo "System configuration files found. Restore? (y/N)"
        read -r restore_system
        
        if [[ "$restore_system" =~ ^[Yy]$ ]]; then
            if [[ -f "$restore_path/system/.gitconfig" ]]; then
                cp "$restore_path/system/.gitconfig" "$HOME/" 2>/dev/null || true
                echo "✅ Restored Git configuration"
            fi
            
            if [[ -d "$restore_path/system/fish" ]]; then
                mkdir -p "$HOME/.config/fish"
                cp -R "$restore_path/system/fish"/* "$HOME/.config/fish/" 2>/dev/null || true
                echo "✅ Restored Fish shell configuration"
            fi
        fi
        
        # Restore Homebrew packages
        if [[ -f "$restore_path/Brewfile" ]]; then
            echo ""
            echo "Homebrew Brewfile found. Install packages? (y/N)"
            read -r restore_brew
            
            if [[ "$restore_brew" =~ ^[Yy]$ ]] && command -v brew >/dev/null 2>&1; then
                cd "$restore_path" && brew bundle install
                echo "✅ Restored Homebrew packages"
            fi
        fi
        
        log_security "INFO" "Configuration restore completed"
        
        # Send notification
        if command -v smart_notify >/dev/null 2>&1; then
            smart_notify "success" "🔒 Configuration Restore" "Configuration restored successfully from backup"
        fi
    fi
    
    rm -rf "$temp_dir"
}

# Security monitoring functions
check_security_status() {
    log_security "INFO" "Starting security status check"
    
    local security_issues=0
    local security_report="$LOG_DIR/security_report_$(date +%Y%m%d).txt"
    
    cat > "$security_report" << EOF
Security Status Report
======================
Generated: $(date)

EOF
    
    # Check file permissions on sensitive files
    echo "FILE PERMISSIONS AUDIT:" >> "$security_report"
    echo "======================" >> "$security_report"
    echo "" >> "$security_report"
    
    # Check SSH directory permissions
    if [[ -d "$HOME/.ssh" ]]; then
        local ssh_perms=$(ls -la "$HOME/.ssh" | awk 'NR>1 {print $1, $9}')
        echo "SSH Directory Contents:" >> "$security_report"
        echo "$ssh_perms" >> "$security_report"
        
        # Check for overly permissive SSH files
        while read -r file; do
            echo "⚠️  SSH file has overly permissive permissions: $file" >> "$security_report"
            ((security_issues++))
        done < <(find "$HOME/.ssh" -type f \( -perm -044 -o -perm -004 \) 2>/dev/null)
    fi
    echo "" >> "$security_report"
    
    # Check for world-writable files in important directories
    echo "WORLD-WRITABLE FILES CHECK:" >> "$security_report"
    echo "==========================" >> "$security_report"
    echo "" >> "$security_report"
    
    local world_writable=$(find "$CONFIG_DIR" -type f -perm -002 2>/dev/null)
    if [[ -n "$world_writable" ]]; then
        echo "⚠️  World-writable files found:" >> "$security_report"
        echo "$world_writable" >> "$security_report"
        ((security_issues++))
    else
        echo "✅ No world-writable files found in maintenance directory" >> "$security_report"
    fi
    echo "" >> "$security_report"
    
    # Check for suspicious processes
    echo "PROCESS MONITORING:" >> "$security_report"
    echo "==================" >> "$security_report"
    echo "" >> "$security_report"
    
    # Look for unusual high-CPU processes
    local high_cpu_procs=$(ps aux | awk '$3 > 80.0 {print $2, $3, $11}' | head -5)
    if [[ -n "$high_cpu_procs" ]]; then
        echo "High CPU processes detected:" >> "$security_report"
        echo "$high_cpu_procs" >> "$security_report"
    else
        echo "✅ No unusual high-CPU processes detected" >> "$security_report"
    fi
    echo "" >> "$security_report"
    
    # Check network connections
    echo "NETWORK CONNECTIONS:" >> "$security_report"
    echo "===================" >> "$security_report"
    echo "" >> "$security_report"
    
    local suspicious_connections=$(netstat -an 2>/dev/null | grep ESTABLISHED | head -10)
    if [[ -n "$suspicious_connections" ]]; then
        echo "Active network connections:" >> "$security_report"
        echo "$suspicious_connections" >> "$security_report"
    fi
    echo "" >> "$security_report"
    
    # Check system integrity
    echo "SYSTEM INTEGRITY:" >> "$security_report"
    echo "=================" >> "$security_report"
    echo "" >> "$security_report"
    
    # Check if maintenance scripts have been modified recently
    local recent_modifications=$(find "$CONFIG_DIR/bin" -name "*.sh" -mtime -1 2>/dev/null)
    if [[ -n "$recent_modifications" ]]; then
        echo "Recently modified scripts (within 24 hours):" >> "$security_report"
        echo "$recent_modifications" >> "$security_report"
    else
        echo "✅ No recently modified maintenance scripts" >> "$security_report"
    fi
    echo "" >> "$security_report"
    
    # Check for failed login attempts (macOS specific)
    echo "LOGIN SECURITY:" >> "$security_report"
    echo "===============" >> "$security_report"
    echo "" >> "$security_report"
    
    local failed_logins=$(log show --predicate 'eventMessage CONTAINS "authentication failure"' --last 24h 2>/dev/null | wc -l | tr -d ' ')
    if [[ ${failed_logins:-0} -gt 5 ]]; then
        echo "⚠️  Multiple failed login attempts detected: $failed_logins" >> "$security_report"
        ((security_issues++))
    else
        echo "✅ No excessive failed login attempts" >> "$security_report"
    fi
    echo "" >> "$security_report"
    
    # Summary
    echo "SECURITY SUMMARY:" >> "$security_report"
    echo "=================" >> "$security_report"
    echo "" >> "$security_report"
    
    if [[ $security_issues -eq 0 ]]; then
        echo "✅ No security issues detected" >> "$security_report"
        log_security "INFO" "Security check passed - no issues found"
    else
        echo "⚠️  $security_issues security issues detected" >> "$security_report"
        echo "Review the details above and take appropriate action" >> "$security_report"
        log_security "WARN" "Security check found $security_issues issues"
        
        # Send security alert
        if command -v security_notification >/dev/null 2>&1; then
            security_notification "system_audit" "$security_issues security issues detected during routine check" "medium"
        fi
    fi
    
    log_security "INFO" "Security report saved to $security_report"
    echo "$security_report"
}

# Backup management functions
list_backups() {
    log_security "INFO" "Listing available backups"
    
    echo "Available Configuration Backups:"
    echo "================================="
    
    if [[ -d "$BACKUP_DIR" ]]; then
        find "$BACKUP_DIR" -name "config_backup_*.tar.gz" -type f | sort -r | while read -r backup; do
            local backup_name=$(basename "$backup")
            local backup_size=$(du -h "$backup" | cut -f1)
            local backup_date=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$backup" 2>/dev/null || stat -c "%y" "$backup" 2>/dev/null | cut -d. -f1)
            
            echo "📦 $backup_name"
            echo "   Size: $backup_size"
            echo "   Date: $backup_date"
            echo "   Path: $backup"
            echo ""
        done
    else
        echo "No backup directory found"
    fi
}

cleanup_old_backups() {
    local retention_days="${1:-30}"
    
    log_security "INFO" "Cleaning up backups older than $retention_days days"
    
    local deleted_count=0
    
    if [[ -d "$BACKUP_DIR" ]]; then
        # Find and delete old backups
        while read -r old_backup; do
            local backup_name=$(basename "$old_backup")
            log_security "INFO" "Deleting old backup: $backup_name"
            rm -f "$old_backup"
            ((deleted_count++))
        done < <(find "$BACKUP_DIR" -name "config_backup_*.tar.gz" -type f -mtime +$retention_days)
        
        if [[ $deleted_count -gt 0 ]]; then
            log_security "INFO" "Deleted $deleted_count old backups"
        else
            log_security "INFO" "No old backups found to delete"
        fi
    fi
}

# Recovery verification
verify_recovery_readiness() {
    log_security "INFO" "Verifying recovery readiness"
    
    local readiness_score=0
    local max_score=100
    
    echo "Recovery Readiness Assessment:"
    echo "============================="
    echo ""
    
    # Check for recent backups
    local recent_backup=$(find "$BACKUP_DIR" -name "config_backup_*.tar.gz" -type f -mtime -7 | head -1)
    if [[ -n "$recent_backup" ]]; then
        echo "✅ Recent backup available (within 7 days)"
        readiness_score=$((readiness_score + 30))
    else
        echo "❌ No recent backup found (recommend creating backup)"
    fi
    
    # Check backup integrity
    if [[ -n "$recent_backup" ]]; then
        if tar -tzf "$recent_backup" >/dev/null 2>&1; then
            if check_backup_safety "$recent_backup" >/dev/null 2>&1; then
                echo "✅ Recent backup integrity and safety verified"
                readiness_score=$((readiness_score + 20))

                # Bonus for checksum
                if [[ -f "${recent_backup}.sha256" ]]; then
                    echo "✅ Backup checksum verified"
                    readiness_score=$((readiness_score + 5))
                else
                    echo "⚠️  Backup lacks checksum file"
                fi
            else
                echo "❌ Recent backup failed safety check"
            fi
        else
            echo "❌ Recent backup appears corrupted"
        fi
    fi
    
    # Check for documentation
    if [[ -f "$CONFIG_DIR/README.md" ]] || [[ -f "$CONFIG_DIR/AUTOMATION_COMPLETE.md" ]]; then
        echo "✅ System documentation available"
        readiness_score=$((readiness_score + 15))
    else
        echo "❌ System documentation missing"
    fi
    
    # Check for recovery scripts
    if [[ -f "$SCRIPT_DIR/security_manager.sh" ]]; then
        echo "✅ Security manager available for recovery operations"
        readiness_score=$((readiness_score + 15))
    else
        echo "❌ Security manager not found"
    fi
    
    # Check external backup location (if configured)
    # This would be customized based on user's backup strategy
    echo "ℹ️  External backup: Configure external storage for additional protection"
    readiness_score=$((readiness_score + 10))
    
    # Check system health
    if [[ -f "$SCRIPT_DIR/system_metrics.sh" ]]; then
        local health_score=$("$SCRIPT_DIR/analytics_dashboard.sh" health 2>/dev/null || echo "0")
        if [[ ${health_score:-0} -gt 70 ]]; then
            echo "✅ System health is good (${health_score}/100)"
            readiness_score=$((readiness_score + 10))
        else
            echo "⚠️  System health needs attention (${health_score}/100)"
            readiness_score=$((readiness_score + 5))
        fi
    fi
    
    echo ""
    echo "Overall Recovery Readiness: ${readiness_score}/${max_score}"
    
    if [[ $readiness_score -ge 80 ]]; then
        echo "Status: ✅ EXCELLENT - System is well-prepared for recovery"
    elif [[ $readiness_score -ge 60 ]]; then
        echo "Status: ✅ GOOD - Minor improvements recommended"
    elif [[ $readiness_score -ge 40 ]]; then
        echo "Status: ⚠️  FAIR - Several improvements needed"
    else
        echo "Status: 🚨 POOR - Critical recovery preparation needed"
    fi
    
    echo ""
    echo "Recommendations:"
    echo "- Create regular automated backups"
    echo "- Test backup restoration periodically"
    echo "- Maintain system documentation"
    echo "- Monitor system health regularly"
    echo "- Consider external backup storage"
    
    log_security "INFO" "Recovery readiness assessment complete: ${readiness_score}/${max_score}"
    
    return 0
}

# Main security manager command
main() {
    case "${1:-status}" in
        "backup")
            backup_config "${2:-incremental}"
            ;;
        "restore")
            local backup_file="${2:-}"
            local mode="${3:-preview}"
            
            if [[ -z "$backup_file" ]]; then
                echo "Usage: $0 restore <backup_file> [preview|restore]"
                echo ""
                list_backups
                exit 1
            fi
            
            restore_config "$backup_file" "$mode"
            ;;
        "list")
            list_backups
            ;;
        "cleanup")
            cleanup_old_backups "${2:-30}"
            ;;
        "security")
            check_security_status
            ;;
        "status"|"check")
            echo "System Security & Backup Status:"
            echo "================================"
            echo ""
            
            # Quick security check
            local security_report=$(check_security_status)
            echo "Security Report: $security_report"
            echo ""
            
            # Backup status
            echo "Recent Backups:"
            list_backups | head -10
            echo ""
            
            # Recovery readiness
            verify_recovery_readiness
            ;;
        "recovery")
            verify_recovery_readiness
            ;;
        *)
            echo "Security & Backup Manager Commands:"
            echo "=================================="
            echo "  backup [full|incremental]     - Create configuration backup"
            echo "  restore <file> [preview|restore] - Restore from backup"
            echo "  list                           - List available backups"
            echo "  cleanup [days]                 - Remove backups older than N days (default: 30)"
            echo "  security                       - Run security audit"
            echo "  status                         - Show overall security and backup status"
            echo "  recovery                       - Assess recovery readiness"
            echo ""
            echo "Examples:"
            echo "  $0 backup full                # Create full backup"
            echo "  $0 restore backup.tar.gz preview  # Preview restore"
            echo "  $0 cleanup 14                 # Delete backups older than 14 days"
            ;;
    esac
}

# If script is run directly, execute main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi

log_security "INFO" "Security manager system loaded successfully"