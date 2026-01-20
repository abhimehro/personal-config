#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🎬 Ultimate Infuse + Cloud Media Library Setup"
echo "=============================================="
echo

# Check if rclone is available
if ! command -v rclone &> /dev/null; then
    echo "❌ rclone not found. Please install it first."
    exit 1
fi

echo "✅ rclone is installed"
echo

# Function to check if remote exists
check_remote() {
    rclone listremotes | grep -q "^$1:$"
}

# Function to setup Google Drive
setup_gdrive() {
    echo "📁 Setting up Google Drive..."
    if check_remote "gdrive"; then
        echo "🔍 Google Drive remote exists, testing connection..."
        if rclone about gdrive: &>/dev/null; then
            echo "✅ Google Drive remote is working"
            return 0
        else
            echo "❌ Google Drive remote has expired authentication"
            echo "🔧 Attempting to reconnect..."
            if rclone config reconnect gdrive: </dev/null; then
                echo "✅ Reconnection successful"
                return 0
            else
                echo "❌ Reconnection failed, will delete and recreate"
                rclone config delete gdrive
                echo "✅ Old remote deleted"
            fi
        fi
    fi

    echo
    echo "🔐 You'll need to authorize Google Drive in your browser"
    echo "Instructions:"
    echo "1. Type 'n' for new remote"
    echo "2. Name: gdrive"
    echo "3. Storage: choose 'drive' (Google Drive)"
    echo "4. Leave client_id/client_secret blank (just press Enter)"
    echo "5. Scope: choose '1' (full access)"
    echo "6. Leave root_folder_id blank"
    echo "7. Service account: choose 'n'"
    echo "8. Auto config: choose 'y' (will open browser)"
    echo "9. Complete authorization in browser"
    echo "10. Team drive: choose 'n' (unless needed)"
    echo "11. Save with 'y'"
    echo
    read -p "Press Enter to start Google Drive setup..."

    rclone config
}

# Function to setup OneDrive
setup_onedrive() {
    echo "📁 Setting up OneDrive..."
    if check_remote "onedrive"; then
        echo "✅ OneDrive remote already exists"
        return 0
    fi

    echo
    echo "🔐 You'll need to authorize OneDrive in your browser"
    echo "Instructions:"
    echo "1. Type 'n' for new remote"
    echo "2. Name: onedrive"
    echo "3. Storage: choose 'onedrive'"
    echo "4. Leave client_id/client_secret blank"
    echo "5. Auto config: choose 'y' (opens browser)"
    echo "6. Complete Microsoft authorization"
    echo "7. Choose account type (personal/business)"
    echo "8. Save with 'y'"
    echo
    read -p "Press Enter to start OneDrive setup..."

    rclone config
}

# Function to create folder structure
create_folders() {
    echo "📂 Creating media folder structure..."

    for remote in gdrive onedrive; do
        if check_remote "$remote"; then
            echo "Creating folders on $remote..."
            rclone mkdir "$remote:Media" 2>/dev/null
            rclone mkdir "$remote:Media/Movies" 2>/dev/null
            rclone mkdir "$remote:Media/TV Shows" 2>/dev/null
            rclone mkdir "$remote:Media/Documentaries" 2>/dev/null
            rclone mkdir "$remote:Media/Kids" 2>/dev/null
            rclone mkdir "$remote:Media/Music" 2>/dev/null
            rclone mkdir "$remote:Media/4K" 2>/dev/null
            echo "✅ Folders created on $remote"
        fi
    done
}

# Function to create union remote
create_union() {
    echo "🔗 Creating unified media remote..."

    # Check if both remotes exist
    if ! check_remote "gdrive" || ! check_remote "onedrive"; then
        echo "❌ Both Google Drive and OneDrive remotes needed for union"
        return 1
    fi

    # Verify Media folders exist
    echo "Checking Media folders..."
    if ! rclone lsd gdrive:Media &>/dev/null; then
        warn "gdrive:Media folder not found, creating..."
        rclone mkdir gdrive:Media
    fi

    if ! rclone lsd onedrive:Media &>/dev/null; then
        warn "onedrive:Media folder not found, creating..."
        rclone mkdir onedrive:Media
    fi

    if check_remote "media"; then
        echo "✅ Media union remote already exists"
        echo "Testing union remote..."
        if rclone lsd media: &>/dev/null; then
            echo "✅ Union remote is working"
            return 0
        else
            warn "Union remote exists but not working, will recreate..."
            rclone config delete media
        fi
    fi

    echo
    echo "Creating union remote that combines Google Drive and OneDrive..."
    echo ""
    echo "CRITICAL: Make sure folder structures match!"
    echo "  Both gdrive:Media and onedrive:Media should have identical structure"
    echo ""
    echo "Instructions:"
    echo "1. Type 'n' for new remote"
    echo "2. Name: media"
    echo "3. Storage: choose 'union'"
    echo "4. Upstreams: gdrive:Media onedrive:Media"
    echo "5. Action policy: epall (or press Enter for default)"
    echo "6. Create policy: epmfs (or press Enter for default)"
    echo "7. Search policy: ff (or press Enter for default)"
    echo "8. Save with 'y'"
    echo
    read -p "Press Enter to create union remote..."

    rclone config

    # Verify union was created correctly
    if check_remote "media"; then
        echo ""
        echo "Testing union remote..."
        if rclone lsd media: &>/dev/null; then
            success "Union remote created and working!"
            echo "Available folders:"
            rclone lsd media: | head -10
        else
            error "Union remote created but not working"
            echo "Check configuration: rclone config show media"
            echo "Verify folders exist: rclone lsd gdrive:Media && rclone lsd onedrive:Media"
        fi
    fi
}

# Function to get local IP
get_local_ip() {
    local ip=$(ipconfig getifaddr en0 2>/dev/null)
    if [[ -z "$ip" ]]; then
        ip="localhost"
    fi
    echo "$ip"
}

# Function to link WebDAV server entrypoint
create_webdav_server() {
    echo "🌐 Linking WebDAV server entrypoint..."

    local target="$REPO_ROOT/media-streaming/scripts/start-media-server-fast.sh"
    local link="$HOME/start-media-server-fast.sh"

    if [[ ! -f "$target" ]]; then
        echo "❌ Missing: $target"
        return 1
    fi

    ln -sf "$target" "$link"
    chmod +x "$target" "$link"
    echo "✅ Linked $link"
}

# Main execution
echo "Let's set up your ultimate media library!"
echo
echo "This will:"
echo "• Set up Google Drive remote"
echo "• Set up OneDrive remote"
echo "• Create organized folder structure"
echo "• Create a unified 'media' remote"
echo "• Set up WebDAV server for Infuse"
echo

read -p "Continue? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 1
fi

# Run setup steps
setup_gdrive
echo
setup_onedrive
echo
create_folders
echo
create_union
echo
create_webdav_server
echo

echo "🎉 Setup Complete!"
echo
echo "📋 What's been set up:"
rclone listremotes
echo
echo "🚀 To start your media server:"
echo "   ~/start-media-server-fast.sh"
echo "   (linked to $REPO_ROOT/media-streaming/scripts/start-media-server-fast.sh)"
echo
echo "🎬 Then add to Infuse:"
echo "   Address: http://$(get_local_ip):8088"
echo "   Username: infuse"
echo "   Password: (see ~/.config/media-server/credentials)"
echo
