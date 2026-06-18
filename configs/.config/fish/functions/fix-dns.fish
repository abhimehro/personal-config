function fix-dns
    # Emergency DNS recovery for Control D
    # Force-kills ctrld, clears static DNS entries on ALL interfaces, and flushes DNS cache
    # Uses dynamic interface detection to work with any network configuration
    
    sudo pkill -9 -f "ctrld run" 2>/dev/null
    sudo launchctl unload /Library/LaunchDaemons/ctrld.plist 2>/dev/null
    
    # Dynamically get all network services and clear DNS on each
    for iface in (networksetup -listallnetworkservices | tail -n +2 | awk '{print $NF}')
        sudo networksetup -setdnsservers "$iface" Empty 2>/dev/null
    end
    
    sudo dscacheutil -flushcache
    sudo killall -HUP mDNSResponder
    echo "DNS restored to DHCP on all interfaces"
end
