function nm-doh6
    # Standalone Control D DoH + IPv6 on (doh-ipv6).
    # Usage: nm-doh6 <privacy|browsing|gaming>
    if test (count $argv) -lt 1
        echo "usage: nm-doh6 <privacy|browsing|gaming>" >&2
        return 1
    end
    cd $NM_ROOT
    env CONTROLD_IPV6=enable ./scripts/network-mode-manager.sh controld $argv[1] doh
end
