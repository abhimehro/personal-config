#!/bin/bash
# Reproduction/Test script for Palette's spinner improvement

LOG_DIR="./test_logs"
mkdir -p "$LOG_DIR"
MASTER_LOG="$LOG_DIR/master.log"

log_status() {
    local msg="$1"
    local target="${2:-$MASTER_LOG}"
    if [[ "$target" == "/dev/stdout" ]]; then
        echo -e "$msg"
    else
        echo -e "$msg" | tee -a "$target"
    fi
}

spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\\'

    # Check if stdout is a TTY
    if [ -t 1 ]; then
        # Hide cursor
        tput civis
        while kill -0 "$pid" 2>/dev/null; do
            local temp=${spinstr#?}
            printf " [%c]  " "$spinstr"
            local spinstr=$temp${spinstr%"$temp"}
            sleep $delay
            printf "\b\b\b\b\b\b"
        done
        # Restore cursor
        tput cnorm
        # Clear spinner
        printf "       \b\b\b\b\b\b\b"
    else
        wait "$pid"
    fi
}

echo "Testing spinner..."
sleep 2 &
spinner $!
echo "Done."

rm -rf "$LOG_DIR"
