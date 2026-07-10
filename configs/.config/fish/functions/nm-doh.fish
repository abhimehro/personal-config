function nm-doh
    # Standalone Control D DoH + IPv6 off (doh-ipv4).
    # Usage: nm-doh <privacy|browsing|gaming>
    if test (count $argv) -lt 1
        echo "usage: nm-doh <privacy|browsing|gaming>" >&2
        return 1
    end
    cd $NM_ROOT; ./scripts/network-mode-manager.sh controld $argv[1] doh
end
