#!/usr/bin/env bash
set -euo pipefail

# ProtonDrive Backup Discovery Script
# Automatically discovers new directories and dotfiles that should be backed up

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_SCRIPT="$SCRIPT_DIR/protondrive_backup.sh"
REPORT_FILE="$HOME/Library/Logs/maintenance/backup_discovery_$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create log directory
mkdir -p "$(dirname "$REPORT_FILE")"

usage() {
  cat << 'EOF'
ProtonDrive Backup Discovery Script

Usage:
  protondrive_backup_discover.sh [OPTIONS]

Options:
  --scan           Scan for new backup candidates (default)
  --report         Generate detailed report
  --dry-run        Show what would be added without making changes
  -h, --help       Show this help message

Examples:
  # Scan for new directories and dotfiles
  ./protondrive_backup_discover.sh --scan

  # Generate detailed report
  ./protondrive_backup_discover.sh --report
EOF
}

log() {
  echo -e "${GREEN}[INFO]${NC} $*" | tee -a "$REPORT_FILE"
}

warn() {
  echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$REPORT_FILE"
}

error() {
  echo -e "${RED}[ERROR]${NC} $*" | tee -a "$REPORT_FILE"
}

section() {
  echo "" | tee -a "$REPORT_FILE"
  echo -e "${BLUE}==== $* ====${NC}" | tee -a "$REPORT_FILE"
  echo "" | tee -a "$REPORT_FILE"
}

# Get currently backed up directories
get_current_backups() {
  local backup_type="$1"
  
  if [ ! -f "$BACKUP_SCRIPT" ]; then
    error "Backup script not found: $BACKUP_SCRIPT"
    return 1
  fi
  
  # Extract CORE or DOTFILES array from script
  sed -n "/${backup_type}=(/,/^)/p" "$BACKUP_SCRIPT" | \
    grep -o '"$HOME/[^"]*"' | \
    sed 's/"$HOME\///; s/"//' | \
    sort
}

# Find potential new directories in HOME
find_new_directories() {
  section "Scanning for New Directories"
  
  # Get currently backed up core directories
  local current_dirs
  current_dirs=$(get_current_backups "CORE")
  
  # Patterns to look for
  local patterns=(
    "Projects*"
    "Work*"
    "Dev*"
    "Code*"
    "Development*"
    "Data*"
    "Media*"
    "Music*"
    "Books*"
    "Notes*"
    "Vault*"
    "Archive*"
    "Sync*"
  )
  
  log "Searching for directories matching patterns: ${patterns[*]}"
  
  local candidates=()
  
  # Find directories in HOME matching patterns
  for pattern in "${patterns[@]}"; do
    while IFS= read -r dir; do
      [ -z "$dir" ] && continue
      
      local basename
      basename=$(basename "$dir")
      
      # Skip if already backed up
      if echo "$current_dirs" | grep -q "^${basename}$"; then
        continue
      fi
      
      # Check if directory is substantial (>10MB and modified recently)
      local size_kb
      size_kb=$(du -sk "$dir" 2>/dev/null | cut -f1 || echo "0")
      local size_mb=$((size_kb / 1024))
      
      local mod_time
      mod_time=$(stat -f "%m" "$dir" 2>/dev/null || echo "0")
      local now
      now=$(date +%s)
      local days_old=$(( (now - mod_time) / 86400 ))
      
      # Suggest if >10MB and modified within last 90 days
      if [ "$size_mb" -gt 10 ] && [ "$days_old" -lt 90 ]; then
        candidates+=("$basename|${size_mb}MB|${days_old}d ago")
      fi
    done < <(find "$HOME" -maxdepth 1 -type d -name "$pattern" 2>/dev/null || true)
  done
  
  if [ ${#candidates[@]} -eq 0 ]; then
    log "No new directories found matching criteria"
    return 0
  fi
  
  log "Found ${#candidates[@]} new directory candidates:"
  echo "" | tee -a "$REPORT_FILE"
  
  printf "%-30s %-15s %-15s\n" "Directory" "Size" "Last Modified" | tee -a "$REPORT_FILE"
  printf "%-30s %-15s %-15s\n" "----------" "----" "-------------" | tee -a "$REPORT_FILE"
  
  for candidate in "${candidates[@]}"; do
    IFS='|' read -r name size modified <<< "$candidate"
    printf "%-30s %-15s %-15s\n" "$name" "$size" "$modified" | tee -a "$REPORT_FILE"
  done
  
  echo "" | tee -a "$REPORT_FILE"
}

# Find potential new dotfiles
find_new_dotfiles() {
  section "Scanning for New Dotfiles"
  
  # Get currently backed up dotfiles
  local current_dotfiles
  current_dotfiles=$(get_current_backups "DOTFILES")
  
  log "Searching for dotfiles and config directories"
  
  local candidates=()
  
  # Find dotfiles/directories in HOME
  while IFS= read -r item; do
    [ -z "$item" ] && continue
    
    local basename
    basename=$(basename "$item")
    
    # Skip if already backed up
    if echo "$current_dotfiles" | grep -q "^${basename}$"; then
      continue
    fi
    
    # Skip common system/cache directories
    case "$basename" in
      .Trash|.cache|.npm|.rustup|.vscode|.cursor|.DS_Store)
        continue
        ;;
    esac
    
    # Check size and modification time
    local size_kb
    if [ -d "$item" ]; then
      size_kb=$(du -sk "$item" 2>/dev/null | cut -f1 || echo "0")
    else
      size_kb=$(stat -f "%z" "$item" 2>/dev/null | awk '{print int($1/1024)}' || echo "0")
    fi
    
    local size_mb=$((size_kb / 1024))
    
    local mod_time
    mod_time=$(stat -f "%m" "$item" 2>/dev/null || echo "0")
    local now
    now=$(date +%s)
    local days_old=$(( (now - mod_time) / 86400 ))
    
    # Suggest if >1MB or modified within last 30 days
    if [ "$size_mb" -gt 1 ] || [ "$days_old" -lt 30 ]; then
      local type
      [ -d "$item" ] && type="dir" || type="file"
      candidates+=("$basename|$type|${size_mb}MB|${days_old}d ago")
    fi
  done < <(find "$HOME" -maxdepth 1 -name ".*" ! -name "." ! -name ".." 2>/dev/null || true)
  
  if [ ${#candidates[@]} -eq 0 ]; then
    log "No new dotfiles found matching criteria"
    return 0
  fi
  
  log "Found ${#candidates[@]} new dotfile/config candidates:"
  echo "" | tee -a "$REPORT_FILE"
  
  printf "%-40s %-10s %-15s %-15s\n" "Path" "Type" "Size" "Last Modified" | tee -a "$REPORT_FILE"
  printf "%-40s %-10s %-15s %-15s\n" "----" "----" "----" "-------------" | tee -a "$REPORT_FILE"
  
  for candidate in "${candidates[@]}"; do
    IFS='|' read -r path type size modified <<< "$candidate"
    printf "%-40s %-10s %-15s %-15s\n" "$path" "$type" "$size" "$modified" | tee -a "$REPORT_FILE"
  done
  
  echo "" | tee -a "$REPORT_FILE"
}

# Main execution
main() {
  local mode="scan"
  
  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --scan|--report)
        mode="${1#--}"
        shift
        ;;
      --dry-run)
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        error "Unknown option: $1"
        usage
        exit 1
        ;;
    esac
  done
  
  section "ProtonDrive Backup Discovery"
  log "Report file: $REPORT_FILE"
  log "Mode: $mode"
  
  find_new_directories
  find_new_dotfiles
  
  section "Summary"
  log "Scan complete!"
  log "Review full report: $REPORT_FILE"
  log ""
  log "Next steps:"
  log "  1. Review discovered items above"
  log "  2. Manually add desired items to: $BACKUP_SCRIPT"
  log "  3. Test changes: $BACKUP_SCRIPT --dry-run"
  log "  4. Run live backup: $BACKUP_SCRIPT --run"
}

main "$@"
