function __ensure_dracula_theme --description 'Reapply Dracula Fish theme only when startup drift is detected'
    set -l marker '--theme=Dracula Official'

    if string match -q "*$marker*" -- "$fish_color_command"; and string match -q "*$marker*" -- "$fish_color_normal"
        return 0
    end

    fish_config theme choose "Dracula Official" >/dev/null 2>&1
end
