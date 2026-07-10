function nm-vpn6
    # Windscribe + Control D with WINDSCRIBE_IPV6=1 (force doh-ipv6).
    # Usage: nm-vpn6 <privacy|browsing|gaming> [location…]
    cd $NM_ROOT
    if test (count $argv) -ge 1
        switch $argv[1]
            case privacy browsing gaming
                env WINDSCRIBE_IPV6=1 ./scripts/windscribe-connect.sh $argv
                return
        end
    end
    env WINDSCRIBE_IPV6=1 ./scripts/network-mode-manager.sh windscribe $argv
end
