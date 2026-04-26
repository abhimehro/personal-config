function nm-vpn
    cd $NM_ROOT
    if test (count $argv) -ge 1
        switch $argv[1]
            case privacy browsing gaming
                ./scripts/windscribe-connect.sh $argv
                return
        end
    end
    ./scripts/network-mode-manager.sh windscribe $argv
end
