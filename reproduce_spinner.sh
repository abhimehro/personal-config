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
    local spin_chars_unicode=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)
    local spin_chars_ascii=('|' '/' '-' '\')
    local spin_chars
    local i=0
    local start_time=$(date +%s)

    # Detect UTF-8 support
    if [[ "${LANG:-}" == *"UTF-8"* ]] || [[ "${LC_ALL:-}" == *"UTF-8"* ]]; then
        spin_chars=("${spin_chars_unicode[@]}")
    else
        spin_chars=("${spin_chars_ascii[@]}")
    fi

    local num_chars=${#spin_chars[@]}

    # Check if stdout is a TTY and not in CI
    if [ -t 1 ] && [ -z "${CI:-}" ]; then
        # Hide cursor
        tput civis 2>/dev/null || true

        trap 'tput cnorm 2>/dev/null || true; exit' INT TERM

        while kill -0 "$pid" 2>/dev/null; do
            local current_time=$(date +%s)
            local elapsed=$((current_time - start_time))

            # Print spinner and elapsed time
            printf "\r %s  Running... (%ds)   " "${spin_chars[i]}" "$elapsed"

            i=$(( (i + 1) % num_chars ))
            sleep $delay
        done

        # Restore cursor
        tput cnorm 2>/dev/null || true

        # Clear the spinner line
        printf "\r\033[K"

        trap - INT TERM
    else
        wait "$pid"
    fi
}

echo "Testing spinner..."
sleep 2 &
spinner $!
echo "Done."

rm -rf "$LOG_DIR"
