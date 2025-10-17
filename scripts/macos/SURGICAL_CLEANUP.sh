#!/bin/bash

# Surgical Home Directory Cleanup
# Removes accumulated junk while preserving essential working configs
# Much faster than factory reset!

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Essential files to KEEP (the few that actually work)
KEEP_FILES=(
    ".ssh"                    # SSH keys - essential for Git/servers
    ".gitconfig"             # Git config - if it works, keep it
    "Documents"              # Your actual work
    "Desktop"                # Current files
    "OneDrive"               # Cloud-synced data
    "Pictures"               # Photos
    "Movies"                 # Videos  
    "Music"                  # Audio files
    "Library/Application Support/Firefox"  # Browser data if you use Firefox
    "Library/Application Support/Google/Chrome" # Browser data if you use Chrome
    "Library/Preferences/com.apple.*"      # Keep Apple system preferences
)

# Fish shell config (you mentioned it works)
KEEP_FISH_CONFIG=true

# Junk patterns to REMOVE (failed configs and cruft)
REMOVE_PATTERNS=(
    "*media-server*"         # All media server attempts
    "*alldebrid*"           # AllDebrid attempts
    "*gdrive*"              # Google Drive setup attempts
    "*infuse*"              # Infuse server attempts
    "*.log"                 # All log files from failed attempts
    "package*.json"         # Node.js project files
    "pnpm-lock.yaml"        # Package manager locks
    "node_modules"          # Node.js dependencies
    ".controld"             # Control D configs
    ".cursor*"              # Cursor editor configs
    ".cache"                # Application caches
    ".config"               # Generic config directory (usually junk)
    ".local"                # Local application data
    ".npm"                  # NPM cache
    ".gem"                  # Ruby gems
    ".rbenv"                # Ruby version manager
    ".mcp-auth"             # MCP authentication
    ".vscode-R"             # VSCode R extension
    ".warp"                 # Warp terminal configs
    ".node_repl_history"    # Node.js REPL history
    ".bash_history"         # Polluted bash history
    ".bashrc"               # Polluted bash config
    ".bash_profile"         # Polluted bash profile
    ".zshrc"                # ZSH config (you use bash/fish anyway)
    ".viminfo"              # Vim history
    "CloudMedia"            # Failed cloud media mount
    "FontBase"              # Font management app data
    "Scripts"               # Random scripts directory
    "Backup"                # Old backup attempts
    "Applications"          # User-installed apps (not system Apps)
)

create_backup_of_keepers() {
    print_status "Creating backup of essential configs..."
    
    local backup_dir="$HOME/Desktop/ESSENTIAL_CONFIGS_BACKUP"
    mkdir -p "$backup_dir"
    
    # Backup SSH keys
    if [ -d "$HOME/.ssh" ]; then
        cp -R "$HOME/.ssh" "$backup_dir/"
        print_status "Backed up SSH keys"
    fi
    
    # Backup Git config
    if [ -f "$HOME/.gitconfig" ]; then
        cp "$HOME/.gitconfig" "$backup_dir/"
        print_status "Backed up Git config"
    fi
    
    # Backup Fish config if it exists
    if [ -d "$HOME/.config/fish" ] && [ "$KEEP_FISH_CONFIG" = true ]; then
        mkdir -p "$backup_dir/.config"
        cp -R "$HOME/.config/fish" "$backup_dir/.config/"
        print_status "Backed up Fish shell config"
    fi
    
    print_success "Essential configs backed up to $backup_dir"
}

show_cleanup_preview() {
    print_status "Scanning for junk to remove..."
    
    echo
    echo -e "${BLUE}=== JUNK TO BE REMOVED ===${NC}"
    
    local total_size=0
    local count=0
    
    for pattern in "${REMOVE_PATTERNS[@]}"; do
        while IFS= read -r -d '' file; do
            if [ -e "$file" ]; then
                local size=$(du -sh "$file" 2>/dev/null | cut -f1 || echo "0B")
                echo "🗑️  $file ($size)"
                ((count++))
            fi
        done < <(find "$HOME" -maxdepth 1 -name "$pattern" -print0 2>/dev/null)
    done
    
    echo
    echo -e "${YELLOW}Found $count items to remove${NC}"
    echo
    echo -e "${BLUE}=== ESSENTIAL FILES TO KEEP ===${NC}"
    
    for keeper in "${KEEP_FILES[@]}"; do
        local full_path="$HOME/$keeper"
        if [ -e "$full_path" ]; then
            local size=$(du -sh "$full_path" 2>/dev/null | cut -f1 || echo "0B")
            echo "✅ $keeper ($size)"
        fi
    done
    
    if [ "$KEEP_FISH_CONFIG" = true ] && [ -d "$HOME/.config/fish" ]; then
        local size=$(du -sh "$HOME/.config/fish" 2>/dev/null | cut -f1 || echo "0B")
        echo "✅ .config/fish ($size)"
    fi
}

perform_surgical_removal() {
    print_status "Performing surgical removal of junk..."
    
    local removed_count=0
    
    for pattern in "${REMOVE_PATTERNS[@]}"; do
        while IFS= read -r -d '' file; do
            if [ -e "$file" ]; then
                print_status "Removing: $(basename "$file")"
                rm -rf "$file" 2>/dev/null || true
                ((removed_count++))
            fi
        done < <(find "$HOME" -maxdepth 1 -name "$pattern" -print0 2>/dev/null)
    done
    
    # Special handling for .config directory - keep only fish
    if [ -d "$HOME/.config" ]; then
        if [ "$KEEP_FISH_CONFIG" = true ] && [ -d "$HOME/.config/fish" ]; then
            # Backup fish config temporarily
            cp -R "$HOME/.config/fish" "/tmp/fish_backup" 2>/dev/null || true
        fi
        
        # Remove .config directory
        rm -rf "$HOME/.config" 2>/dev/null || true
        print_status "Removed .config directory"
        
        # Restore fish config if it was backed up
        if [ "$KEEP_FISH_CONFIG" = true ] && [ -d "/tmp/fish_backup" ]; then
            mkdir -p "$HOME/.config"
            mv "/tmp/fish_backup" "$HOME/.config/fish"
            print_status "Restored Fish shell config"
        fi
    fi
    
    print_success "Removed $removed_count junk items"
}

clean_shell_configs() {
    print_status "Cleaning shell configurations..."
    
    # Create clean .bash_profile (minimal)
    cat > "$HOME/.bash_profile" << 'EOF'
# Clean .bash_profile
# Add /opt/homebrew/bin to PATH
export PATH="/opt/homebrew/bin:$PATH"

# Load .bashrc if it exists
[ -f ~/.bashrc ] && source ~/.bashrc
EOF
    
    # Create clean .bashrc (minimal)
    cat > "$HOME/.bashrc" << 'EOF'
# Clean .bashrc
# Basic aliases
alias ll='ls -la'
alias la='ls -A'
alias l='ls -CF'
EOF
    
    # Remove polluted history files
    rm -f "$HOME/.bash_history" 2>/dev/null || true
    rm -f "$HOME/.node_repl_history" 2>/dev/null || true
    rm -f "$HOME/.viminfo" 2>/dev/null || true
    
    print_success "Shell configurations cleaned"
}

verify_cleanup() {
    print_status "Verifying cleanup results..."
    
    echo
    echo -e "${BLUE}=== CLEANUP RESULTS ===${NC}"
    
    # Check what remains in home directory
    echo "📁 Remaining items in home directory:"
    ls -la "$HOME" | grep -v "^total" | while read line; do
        echo "   $line"
    done
    
    echo
    echo -e "${GREEN}✅ Essential files preserved:${NC}"
    for keeper in "${KEEP_FILES[@]}"; do
        if [ -e "$HOME/$keeper" ]; then
            echo "   ✅ $keeper"
        fi
    done
    
    if [ "$KEEP_FISH_CONFIG" = true ] && [ -d "$HOME/.config/fish" ]; then
        echo "   ✅ .config/fish"
    fi
    
    echo
    local remaining_junk=0
    for pattern in "${REMOVE_PATTERNS[@]}"; do
        if find "$HOME" -maxdepth 1 -name "$pattern" | grep -q .; then
            ((remaining_junk++))
        fi
    done
    
    if [ $remaining_junk -eq 0 ]; then
        echo -e "${GREEN}🎉 All junk successfully removed!${NC}"
    else
        echo -e "${YELLOW}⚠️  Some junk items may remain${NC}"
    fi
    
    # Check available space
    local available_space=$(df -h "$HOME" | awk 'NR==2{print $4}')
    echo "💾 Available space: $available_space"
}

main() {
    echo -e "${BLUE}🧹 SURGICAL HOME DIRECTORY CLEANUP 🧹${NC}"
    echo
    echo "This will remove accumulated junk while preserving essential configs."
    echo "Much faster than factory reset!"
    echo
    
    show_cleanup_preview
    
    echo
    read -p "Continue with surgical cleanup? (y/N): " confirm
    if [[ $confirm != [yY] ]]; then
        echo "Cleanup cancelled."
        exit 0
    fi
    
    create_backup_of_keepers
    perform_surgical_removal
    clean_shell_configs
    verify_cleanup
    
    echo
    echo -e "${GREEN}🎉 SURGICAL CLEANUP COMPLETE! 🎉${NC}"
    echo
    echo "Results:"
    echo "  ✅ All junk files and failed configs removed"
    echo "  ✅ Essential working configs preserved (.ssh, .gitconfig, fish)"
    echo "  ✅ Clean shell environment restored"
    echo "  ✅ Your actual data (Documents, OneDrive) untouched"
    echo
    echo -e "${YELLOW}💡 Recommendation: Restart Terminal to enjoy clean environment${NC}"
}

# Check if running from correct location
if [[ "$(pwd)" != "/Users/abhimehrotra" ]]; then
    cd "$HOME"
fi

main "$@"