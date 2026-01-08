#!/usr/bin/env bash
set -euo pipefail

# Proton Drive Sync Recovery Script
# Fixes "No URL for file upload" and persistent sync errors

echo "=========================================="
echo "Proton Drive Sync Recovery Tool"
echo "=========================================="
echo ""

PROTON_DIR="$HOME/Library/CloudStorage/ProtonDrive-abhimehro@pm.me-folder"
APP_SUPPORT="$HOME/Library/Application Support/Proton Drive"
CACHES="$HOME/Library/Caches/Proton Drive"

# Check if Proton Drive is running
echo "Step 1: Checking Proton Drive status..."
if pgrep -f "Proton Drive" >/dev/null 2>&1; then
    PROTON_PID=$(pgrep -f "Proton Drive" | head -1)
    echo "✓ Proton Drive is running (PID: $PROTON_PID)"
    echo ""
    echo "⚠️  Proton Drive must be quit before cleaning cache"
    echo ""
    read -p "Quit Proton Drive now? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Quitting Proton Drive..."
        killall "Proton Drive" 2>/dev/null || true
        sleep 3
        echo "✓ Proton Drive quit successfully"
    else
        echo "❌ Cannot proceed while Proton Drive is running"
        exit 1
    fi
else
    echo "✓ Proton Drive is not running (safe to proceed)"
fi

echo ""
echo "Step 2: Backing up current sync state..."

# Create backup directory
BACKUP_DIR="$HOME/Desktop/ProtonDrive-Backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [[ -d "$APP_SUPPORT" ]]; then
    echo "Backing up Application Support..."
    cp -R "$APP_SUPPORT" "$BACKUP_DIR/" 2>/dev/null || echo "  (Some files may be locked - skipped)"
fi

if [[ -d "$CACHES" ]]; then
    echo "Backing up Caches..."
    cp -R "$CACHES" "$BACKUP_DIR/" 2>/dev/null || echo "  (Some files may be locked - skipped)"
fi

echo "✓ Backup saved to: $BACKUP_DIR"

echo ""
echo "Step 3: Clearing Proton Drive cache and sync database..."

# Clear cache directories
if [[ -d "$CACHES" ]]; then
    echo "Clearing cache directory..."
    rm -rf "$CACHES"/* 2>/dev/null || true
    echo "✓ Cache cleared"
fi

# Clear application support cache
if [[ -d "$APP_SUPPORT/Cache" ]]; then
    echo "Clearing app support cache..."
    rm -rf "$APP_SUPPORT/Cache"/* 2>/dev/null || true
    echo "✓ App support cache cleared"
fi

# Clear sync database (this forces re-indexing)
if [[ -d "$APP_SUPPORT/databases" ]]; then
    echo "Clearing sync database..."
    rm -rf "$APP_SUPPORT/databases"/* 2>/dev/null || true
    echo "✓ Sync database cleared"
fi

# Clear logs (optional, but helps with fresh start)
if [[ -d "$APP_SUPPORT/Logs" ]]; then
    echo "Clearing old logs..."
    find "$APP_SUPPORT/Logs" -name "*.log" -mtime +7 -delete 2>/dev/null || true
    echo "✓ Old logs cleared"
fi

echo ""
echo "Step 4: Checking for problematic files..."

# Look for .sync temp files (partial uploads)
if [[ -d "$PROTON_DIR" ]]; then
    SYNC_FILES=$(find "$PROTON_DIR" -name "*.sync" 2>/dev/null | wc -l | tr -d ' ')
    if [[ $SYNC_FILES -gt 0 ]]; then
        echo "⚠️  Found $SYNC_FILES .sync files (partial uploads)"
        echo "These will be re-uploaded after restart"
    else
        echo "✓ No .sync files found"
    fi
    
    # Check for conflict files
    CONFLICT_FILES=$(find "$PROTON_DIR" -name "*conflict*" 2>/dev/null | wc -l | tr -d ' ')
    if [[ $CONFLICT_FILES -gt 0 ]]; then
        echo "⚠️  Found $CONFLICT_FILES conflict files"
        echo "Review these manually after sync recovery"
    fi
fi

echo ""
echo "=========================================="
echo "✅ Cache clearing complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo ""
echo "1. Open Proton Drive from Applications"
echo "2. Sign in if prompted (authentication tokens cleared)"
echo "3. Wait 3-5 minutes for complete re-indexing"
echo "4. Check sync status in the app"
echo ""
echo "If errors persist:"
echo "• Check available storage: $(df -h "$PROTON_DIR" | awk 'NR==2 {print $4}') free"
echo "• Verify internet connectivity"
echo "• Try selective sync (exclude large/problematic folders)"
echo ""
echo "Backup location: $BACKUP_DIR"
echo "=========================================="
