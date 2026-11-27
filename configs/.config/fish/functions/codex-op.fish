# codex-op: Launch Codex with 1Password-injected MCP environment variables.
#
# The committed .codex/config.toml forwards keys by name only (env_vars /
# env_http_headers); this wrapper supplies the values from 1Password for the
# duration of the Codex process. See docs/MCP_SECRETS_MANAGEMENT.md.
#
# SECURITY: op:// references are function-scoped and resolved by `op run` only
# for the Codex child process. Nothing is written to disk and keys are never
# present in the interactive shell after launch.

function codex-op --description 'Launch Codex with 1Password-injected MCP environment variables'
    op-ready or return 1

    # Devin needs the full "Bearer <token>" header; op run cannot resolve a
    # ref embedded mid-string, so read the token and compose the header here.
    # The value lives only in this local variable for the duration of launch.
    set -l devin_token (op read 'op://Personal/DEVIN_API_KEY/credential' 2>/dev/null)
    if test -z "$devin_token"
        echo "codex-op: failed to read DEVIN_API_KEY from 1Password" >&2
        return 1
    end

    # op run resolves these op:// references into real values for the child
    # process only.
    set -lx BRAVE_API_KEY "op://Personal/BRAVE_API_KEY/credential"
    set -lx EXA_API_KEY "op://Personal/EXA_API_KEY/credential"
    set -lx PERPLEXITY_API_KEY "op://Personal/PERPLEXITY_RAYCAST_API_KEY/credential"
    set -lx TAVILY_API_KEY "op://Personal/TAVILY_API_KEY/credential"
    set -lx FIRECRAWL_API_KEY "op://Personal/FIRECRAWL_API_KEY/credential"
    set -lx DEVIN_MCP_AUTH_HEADER "Bearer $devin_token"
    set -lx CONTEXT7_API_KEY "op://Personal/CONTEXT7_API_KEY/credential"

    op run -- /opt/homebrew/bin/codex $argv
end
