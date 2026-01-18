#!/usr/bin/env bash
set -euo pipefail

echo "💾 Starting Document Backup..."
echo "=================================="

BACKUP_DIR="$HOME/Backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="documents_backup_$TIMESTAMP"
FULL_BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

mkdir -p "$BACKUP_DIR"

echo "📁 Backup location: $FULL_BACKUP_PATH"
echo ""

backup_directory() {
    local source_dir="$1"
    local backup_subdir="$2"
    if [ -d "$source_dir" ]; then
        echo "📂 Backing up $source_dir..."
        mkdir -p "$FULL_BACKUP_PATH/$backup_subdir"
        rsync -av --exclude='.DS_Store' --exclude='*.tmp' "$source_dir/" "$FULL_BACKUP_PATH/$backup_subdir/" >/dev/null 2>&1 || true
        local file_count=$(find "$source_dir" -type f | wc -l | xargs)
        local size=$(du -sh "$source_dir" 2>/dev/null | cut -f1)
        echo "   ✅ $file_count files ($size) backed up"
    else
        echo "   ⚠️  Directory $source_dir not found, skipping"
    fi
}

# Core folders
backup_directory "$HOME/Documents" "Documents"
backup_directory "$HOME/Desktop" "Desktop"
backup_directory "$HOME/Scripts" "Scripts"

echo ""
echo "⚙️  Backing up application preferences..."

# Raycast settings
if [ -d "$HOME/Library/Application Support/com.raycast.macos" ]; then
    backup_directory "$HOME/Library/Application Support/com.raycast.macos" "AppData/Raycast"
fi

# SSH keys (public + config only)
if [ -d "$HOME/.ssh" ]; then
    echo "🔑 Backing up SSH config and public keys..."
    mkdir -p "$FULL_BACKUP_PATH/Config/ssh"
    cp "$HOME/.ssh/config" "$FULL_BACKUP_PATH/Config/ssh/" 2>/dev/null || true
    cp "$HOME/.ssh/"*.pub "$FULL_BACKUP_PATH/Config/ssh/" 2>/dev/null || true
fi

# Git configuration
if [ -f "$HOME/.gitconfig" ]; then
    echo "🌿 Backing up Git configuration..."
    mkdir -p "$FULL_BACKUP_PATH/Config"
    cp "$HOME/.gitconfig" "$FULL_BACKUP_PATH/Config/" 2>/dev/null || true
fi

# Shell configurations
echo "🐚 Backing up shell configurations..."
mkdir -p "$FULL_BACKUP_PATH/Config/shell"
for config_file in .zshrc .bashrc .bash_profile .profile .vimrc .tmux.conf; do
    if [ -f "$HOME/$config_file" ]; then
        cp "$HOME/$config_file" "$FULL_BACKUP_PATH/Config/shell/" 2>/dev/null || true
    fi
done

# Create compressed archive
echo ""
echo "📦 Creating compressed archive..."
cd "$BACKUP_DIR"
if tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME" >/dev/null 2>&1; then
    rm -rf "$BACKUP_NAME"
    archive_size=$(du -sh "${BACKUP_NAME}.tar.gz" | cut -f1)
    echo "   ✅ Archive created: ${BACKUP_NAME}.tar.gz ($archive_size)"
else
    echo "   ⚠️  Archive creation failed, keeping uncompressed backup"
fi

# Cleanup old backups (keep last 5)
echo ""
echo "🧹 Cleaning up old backups (keeping latest 5)..."
backup_files=($(ls -1t "$BACKUP_DIR"/documents_backup_*.tar.gz 2>/dev/null || true))
if [ ${#backup_files[@]} -gt 5 ]; then
    for ((i=5; i<${#backup_files[@]}; i++)); do
        rm -f "${backup_files[$i]}"
        echo "   🗑️  Removed: $(basename "${backup_files[$i]}")"
    done
    echo "   ✅ Cleanup complete"
else
    echo "   ✅ No cleanup needed (${#backup_files[@]} backups total)"
fi

echo ""
echo "=================================="
echo "✅ Backup completed successfully!"
echo "📊 Backup summary:"
echo "   📁 Location: $BACKUP_DIR"
echo "   📦 Latest: ${BACKUP_NAME}.tar.gz"
echo "   📈 Total backups: $(ls -1 "$BACKUP_DIR"/documents_backup_*.tar.gz 2>/dev/null | wc -l | xargs)"
echo "   💾 Total backup size: $(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)"
echo "🕐 Completed at: $(date)"
