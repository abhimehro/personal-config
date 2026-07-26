# Full restart of the media infrastructure (server, mount, renamer)
function media-restart
    echo "\u{1f504} Restarting media infrastructure..."

    set -l agents \
        "com.speedybee.media.renamer" \
        "com.speedybee.media.mount" \
        "com.speedybee.media.server"

    for agent in $agents
        echo "  Restarting $agent..."
        launchctl stop "$agent" 2>/dev/null || true
        sleep 2
        launchctl start "$agent"
    end

    echo ""
    media-status
end
