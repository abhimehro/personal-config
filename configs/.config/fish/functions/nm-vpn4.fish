function nm-vpn4
    # Windscribe + Control D with WINDSCRIBE_IPV6=0 (force doh-ipv4).
    # Usage: nm-vpn4 <privacy|browsing|gaming> [location…]
    cd $NM_ROOT
    if test (count $argv) -ge 1
        switch $argv[1]
            case privacy browsing gaming
                env WINDSCRIBE_IPV6=0 ./scripts/windscribe-connect.sh $argv
                return
        end
    end
    env WINDSCRIBE_IPV6=0 ./scripts/network-mode-manager.sh windscribe $argv
end
