function _op_inject --description 'Run a command with 1Password op:// env refs resolved at runtime'
    argparse 'e/env=' -- $argv
    or return 1

    op-ready
    or return $status

    for pair in $_flag_env
        set -l parts (string split -m 1 = -- $pair)
        if test (count $parts) -lt 2
            echo "_op_inject: invalid -e pair (expected KEY=op://...): $pair" >&2
            return 1
        end

        set -l var_name $parts[1]
        set -l var_value $parts[2]
        set -lx $var_name $var_value
    end

    op run -- $argv
end
