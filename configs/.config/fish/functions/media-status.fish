# Check media agents (WebDAV server, mount, renamer) + optional Jellyfin
function media-status
    set -l agents "com.speedybee.media.server" "com.speedybee.media.mount" "com.speedybee.media.renamer"
    set -l optional_agents "com.speedybee.jellyfin"

    set -l all_running true

    for agent in $agents
        if launchctl list | grep -q "$agent"
            set -l pid (launchctl list | grep "$agent" | awk '{print $1}')
            echo "✅ $agent: RUNNING (PID: $pid)"
        else
            echo "❌ $agent: NOT RUNNING"
            set all_running false
        end
    end

    for agent in $optional_agents
        if launchctl list | grep -q "$agent"
            set -l pid (launchctl list | grep "$agent" | awk '{print $1}')
            echo "✅ $agent: RUNNING (PID: $pid)"
        else
            echo "⚪ $agent: not loaded (run setup-jellyfin-native.sh after install)"
        end
    end

    if test "$all_running" = "true"
        echo ""
        echo "🎬 Core media agents are running!"
    else
        echo ""
        echo "⚠️  Some core media agents are not running!"
    end
end
