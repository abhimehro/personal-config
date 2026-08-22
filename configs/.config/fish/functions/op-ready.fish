function op-ready --description 'Ensure 1Password CLI session is active (lazy check; never run at shell startup)'
    if not type -q op
        echo "op-ready: 1Password CLI (op) not found" >&2
        return 127
    end

    op whoami >/dev/null 2>&1
    if test $status -ne 0
        echo "1Password session expired — run: op signin" >&2
        return 1
    end
end
