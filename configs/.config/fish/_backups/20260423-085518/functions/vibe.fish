function vibe --description 'Switch vibe presets'
    if test (count $argv) -eq 0
        echo 'Usage: vibe <preset> [extra args...]'
        return 1
    end

    ~/.local/bin/auto_vibe.sh $argv
    and echo "✨ Vibe switched to: $argv[1]"
end
