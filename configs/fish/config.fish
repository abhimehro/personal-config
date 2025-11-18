# Add Homebrew and user bin to PATH
fish_add_path /opt/homebrew/bin
fish_add_path ~/bin

if status is-interactive
    # Commands to run in interactive sessions can go here
end
