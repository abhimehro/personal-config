function nm-status
    # Prefer one-screen Control D health when present; fall back to full nm status.
    if test -x $NM_ROOT/scripts/controld-status.sh
        $NM_ROOT/scripts/controld-status.sh
        echo ""
    end
    cd $NM_ROOT; ./scripts/network-mode-manager.sh status
end
