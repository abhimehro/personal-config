function fish_greeting
    # Rotating greetings
    set -l greetings "Hello!" "Namaste!" "Howdy!" "Hey there!" "Welcome back!"

    # Pick a random greeting
    set -l random_index (random 1 (count $greetings))
    set -l greeting $greetings[$random_index]

    # Display greeting with some style
    echo (set_color cyan)"$greeting"(set_color normal)" Ready to code? 🚀"
end
