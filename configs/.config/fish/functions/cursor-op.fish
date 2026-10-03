function cursor-op --description 'Launch Cursor with 1Password-injected MCP environment variables'
    op-ready or return 1

    set -l ctx7_key (op read 'op://Personal/CONTEXT7_API_KEY/credential' 2>/dev/null)
    if test -z "$ctx7_key"
        echo "cursor-op: failed to read CONTEXT7_API_KEY from 1Password" >&2
        return 1
    end

    # SECURITY: export for Cursor child process; tracked .cursor/mcp.json uses ${env:CONTEXT7_API_KEY}
    set -gx CONTEXT7_API_KEY "$ctx7_key"
    open -a Cursor $argv
end
