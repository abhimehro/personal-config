# codex-op: Launch Codex with 1Password-injected MCP environment variables.
#
# Both the repo-level (.codex/config.toml) and user-level (~/.codex/config.toml)
# configs forward keys by name only (env_vars / env_http_headers /
# bearer_token_env_var); this wrapper supplies the values from 1Password for the
# duration of the Codex process. See docs/MCP_SECRETS_MANAGEMENT.md.
#
# SECURITY: op:// references are function-scoped and resolved by `op run` only
# for the Codex child process. Nothing is written to disk and keys are never
# present in the interactive shell after launch.

function codex-op --description 'Launch Codex with 1Password-injected MCP environment variables'
    op-ready or return 1

    # Headers needing a composed "Bearer <token>" value: op run cannot resolve
    # a ref embedded mid-string, so read the token and compose the header here.
    # Values live only in local variables for the duration of launch.
    set -l devin_token (op read 'op://Personal/DEVIN_API_KEY/credential' 2>/dev/null)
    if test -z "$devin_token"
        echo "codex-op: failed to read DEVIN_API_KEY from 1Password" >&2
        return 1
    end
    set -l plan_token (op read 'op://Personal/PLAN_MCP_AUTH_HEADER/credential' 2>/dev/null)
    if test -z "$plan_token"
        echo "codex-op: failed to read PLAN_MCP_AUTH_HEADER from 1Password" >&2
        return 1
    end
    set -l raycast_token (op read 'op://Personal/RAYCAST_MCP_AUTH_HEADER/credential' 2>/dev/null)
    if test -z "$raycast_token"
        echo "codex-op: failed to read RAYCAST_MCP_AUTH_HEADER from 1Password" >&2
        return 1
    end

    # op run resolves these op:// references into real values for the child
    # process only.
    set -lx BRAVE_API_KEY "op://Personal/BRAVE_API_KEY/credential"
    set -lx EXA_API_KEY "op://Personal/EXA_API_KEY/credential"
    set -lx PERPLEXITY_API_KEY "op://Personal/PERPLEXITY_RAYCAST_API_KEY/credential"
    set -lx TAVILY_API_KEY "op://Personal/TAVILY_API_KEY/credential"
    set -lx FIRECRAWL_API_KEY "op://Personal/FIRECRAWL_API_KEY/credential"
    set -lx CONTEXT7_API_KEY "op://Personal/CONTEXT7_API_KEY/credential"
    set -lx GITHUB_MCP_TOKEN "op://Personal/bxu5w3uhxihr24ptygbbwzrlce/token"
    set -lx DEVIN_MCP_AUTH_HEADER "Bearer $devin_token"
    set -lx PLAN_MCP_AUTH_HEADER "Bearer $plan_token"
    set -lx RAYCAST_MCP_AUTH_HEADER "Bearer $raycast_token"

    op run -- /opt/homebrew/bin/codex $argv
end
