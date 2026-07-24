# Stream logs for media server and mount
function media-logs
    echo "=== Media Server Log ==="
    tail -f ~/Library/Logs/media-server.log &
    echo "=== Media Mount Log ==="
    tail -f ~/Library/Logs/media-mount.log
end
