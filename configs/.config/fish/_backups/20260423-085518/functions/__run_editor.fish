function __run_editor --description 'Run $EDITOR while preserving any arguments in its definition'
    set -l editor (string split ' ' -- $EDITOR)
    command $editor $argv
end
