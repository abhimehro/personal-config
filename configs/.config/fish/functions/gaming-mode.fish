# Toggle media infrastructure for latency-critical gaming (GeForce NOW).
# Chains with nm-gaming (network profile) so one command handles both.
#
# USAGE:
#   gaming-mode           Toggle media stack on/off
#   gaming-mode on|off|status
#   gaming-mode net ...   Pass-through to nm-gaming (network-mode-manager)
function gaming-mode
    set -l script ~/dev/personal-config/media-streaming/scripts/gaming-mode.sh

    # Pass-through to the network manager if subcommand is "net"
    if test (count $argv) -gt 0; and test $argv[1] = net
        set -e argv[1]
        nm-gaming $argv
        return $status
    end

    bash $script $argv
    set -l rc $status

    # Keep the network gaming profile in sync with the media stack state.
    if test (count $argv) -eq 0; or contains -- $argv[1] on off
        if test -x $NM_ROOT/scripts/network-mode-manager.sh; or test -n "$NM_ROOT"
            if test $rc -eq 0
                echo ""
                echo "Tip: network profile unchanged. Run nm-gaming to switch ControlD to gaming."
            end
        end
    end
    return $rc
end
