#!/usr/bin/env bash
# ==============================================================================
# PHASE 2: BACKLOG MINER ORCHESTRATOR & SUMMARY GENERATOR
# ==============================================================================
# Part of SecOps Autopilot
# Cadence: Bi-weekly / Monthly (1st and 15th at 10:00 AM)
# ==============================================================================
set -Eeuo pipefail

DEV_ROOT="$HOME/dev"
REPOS=(
	"personal-config"
	"ctrld-sync"
	"email-security-pipeline"
	"Seatek_Analysis"
	"Hydrograph_Versus_Seatek_Sensors_Project"
	"series_correction_project_updated"
)
LOG_FILE="$HOME/.backlog-miner-history.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >>"$LOG_FILE"; }

echo "=============================================================================="
echo "Starting Phase 2: Backlog Miner & Triage Orchestrator"
echo "=============================================================================="
log "START - Phase 2 run begin."

# This script can serve as the kickoff agent. It checks the presence of the active task tracker or 'lessons.md'
# across all repositories and logs a status update of your technical debt files.

for repo in "${REPOS[@]}"; do
	dir="$DEV_ROOT/$repo"
	if [ ! -d "$dir/.git" ]; then
		echo "skip: $repo (not a git repo)"
		continue
	fi

	echo "==> Mining repo structure for: $repo"

	tasks_dir="$dir/tasks"
	lessons_file="$tasks_dir/lessons.md"
	todo_file="$tasks_dir/todo.md"

	if [ -f "$todo_file" ]; then
		open_todos=$(grep -c "^- \[ \]" "$todo_file" 2>/dev/null || true)
		open_todos=${open_todos:-0}
		completed_todos=$(grep -c "^- \[x\]" "$todo_file" 2>/dev/null || true)
		completed_todos=${completed_todos:-0}
		echo "  Found tasks/todo.md: $open_todos open, $completed_todos completed tasks."
		log "INFO - $repo: $open_todos open, $completed_todos completed tasks."
	else
		echo "  No tasks/todo.md file exists."
		log "INFO - $repo: No todo.md found."
	fi

	if [ -f "$lessons_file" ]; then
		lessons_count=$(grep -c "^#" "$lessons_file" 2>/dev/null || true)
		lessons_count=${lessons_count:-0}
		echo "  Found tasks/lessons.md: ~$lessons_count rule records / titles."
	else
		echo "  No tasks/lessons.md file exists."
	fi
done

echo ""
echo "=============================================================================="
echo "HOW TO RUN REFACTOR MINING:"
echo "------------------------------------------------------------------------------"
echo "To execute a deep-dive scan using Repo Prompt and Windsurf/Cursor, paste the"
echo "systematic refactoring prompt located in ~/secops/README.md into your active"
echo "reasoning window. Focus on 1-2 directories inside one of the repos listed above."
echo "=============================================================================="

log "SUCCESS - Backlog structure audit complete."
