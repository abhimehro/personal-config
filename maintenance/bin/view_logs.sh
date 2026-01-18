#!/usr/bin/env bash

# Log Viewer Script - Opens maintenance logs in a user-friendly way
# Usage: view_logs.sh [task_name|summary]

set -eo pipefail

LOG_DIR="$HOME/Library/Logs/maintenance"
TASK="$1"

# Colors for UX
BOLD=$(tput bold 2>/dev/null || echo "")
CYAN=$(tput setaf 6 2>/dev/null || echo "")
GREEN=$(tput setaf 2 2>/dev/null || echo "")
RED=$(tput setaf 1 2>/dev/null || echo "")
RESET=$(tput sgr0 2>/dev/null || echo "")

open_files() {
    local files=("$@")
    if [[ ${#files[@]} -eq 0 ]]; then
        echo "${RED}No log files found for: ${TASK:-selection}${RESET}"
        return 1
    fi
    echo "${GREEN}Opening ${#files[@]} file(s)...${RESET}"
    
    if command -v open >/dev/null 2>&1; then
        for file in "${files[@]}"; do open -a TextEdit "$file" 2>/dev/null || open "$file"; done
    elif command -v less >/dev/null 2>&1; then
        less -R "${files[@]}"
    else
        cat "${files[@]}"
    fi
}

# Interactive Mode (No args)
if [[ -z "$TASK" ]]; then
    echo "${BOLD}${CYAN}Maintenance Log Viewer${RESET}"
    mapfile -t LOGS < <(find "$LOG_DIR" -maxdepth 1 -type f \( -name "*.log" -o -name "*.txt" \) 2>/dev/null | sort -r | head -10)
    
    if [[ ${#LOGS[@]} -eq 0 ]]; then
        echo "${RED}No logs found in $LOG_DIR${RESET}"
        exit 0
    fi

    PS3="${BOLD}Select a log to view (1-${#LOGS[@]}): ${RESET}"
    select opt in "${LOGS[@]##*/}" "Quit"; do
        if [[ -n "$opt" && "$opt" != "Quit" ]]; then
            open_files "$LOG_DIR/$opt"
            break
        elif [[ "$opt" == "Quit" ]]; then
            break
        fi
    done
    exit 0
fi

# Argument Mode
if [[ "$TASK" == "summary" ]]; then
    FILE=$(ls -t "$LOG_DIR"/error_summary_*.txt 2>/dev/null | head -1 || true)
    [[ -n "$FILE" ]] && open_files "$FILE" || echo "${RED}No error summary found.${RESET}"
else
    mapfile -t FILES < <(find "$LOG_DIR" -type f -iname "*${TASK}*.log" 2>/dev/null | sort -r | head -5)
    open_files "${FILES[@]}"
fi
