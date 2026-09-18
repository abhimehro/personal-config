#!/usr/bin/env bash

# Prefer caller/test HOME; default only when unset (Linux CI must not mkdir /Users).
export HOME="${HOME:-/Users/speedybee}"

# Self-contained quick cleanup script
# Note: Using -o pipefail but NOT -e to allow graceful permission handling
set -o pipefail

# Configuration
LOG_DIR="$HOME/Library/Logs/maintenance"
mkdir -p "$LOG_DIR"

# Basic logging
log_info() {
	local ts
	ts="$(date '+%Y-%m-%d %H:%M:%S')"
	echo "$ts [INFO] [quick_cleanup] $*" | tee -a "$LOG_DIR/quick_cleanup.log"
}

log_warn() {
	local ts
	ts="$(date '+%Y-%m-%d %H:%M:%S')"
	echo "$ts [WARNING] [quick_cleanup] $*" | tee -a "$LOG_DIR/quick_cleanup.log"
}

# Load config
CONFIG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../conf" && pwd)/config.env"
if [[ -f $CONFIG_FILE ]]; then
	# shellcheck disable=SC1090
	source "$CONFIG_FILE" 2>/dev/null || true
fi

log_info "Quick cleanup started"

CLEANED=0

# 1) Clear user caches
log_info "Cleaning user caches..."
if [[ -d "$HOME/Library/Caches" ]]; then
	# Clean application caches (but preserve important ones)
	for cache_dir in "$HOME/Library/Caches"/*; do
		if [[ -d $cache_dir ]]; then
			# Skip system-critical caches
			# NOTE: bash-native expansion; avoids fork per iteration
			case "${cache_dir##*/}" in
			com.apple.* | CloudKit | CrashReporter | SkyLight) continue ;;
			esac

			# Clean cache if older than configured days (with permission handling)
			has_old_files=0
			if command -v fd >/dev/null 2>&1; then
				if fd . "$cache_dir" --type f --changed-before "${CLEANUP_CACHE_DAYS:-30}d" --max-results 1 &>/dev/null; then
					has_old_files=1
				fi
			else
				if find "$cache_dir" -type f -mtime +"${CLEANUP_CACHE_DAYS:-30}" -print -quit 2>/dev/null | grep -q .; then
					has_old_files=1
				fi
			fi

			if [[ $has_old_files -eq 1 ]]; then
				if command -v fd >/dev/null 2>&1; then
					if fd . "$cache_dir" --type f --changed-before "${CLEANUP_CACHE_DAYS:-30}d" -x rm 2>/dev/null; then
						((CLEANED++))
					else
						log_warn "Could not clean some files in ${cache_dir##*/} (permission denied)"
					fi
				else
					if find "$cache_dir" -type f -mtime +"${CLEANUP_CACHE_DAYS:-30}" -delete 2>/dev/null; then
						((CLEANED++))
					else
						log_warn "Could not clean some files in ${cache_dir##*/} (permission denied)"
					fi
				fi
			fi
		fi
	done
fi

# 2) Clean Downloads folder (old files)
log_info "Cleaning old downloads..."
if [[ -d "$HOME/Downloads" ]]; then
	# Count files before cleanup (handle permission errors)
	BEFORE_COUNT=$(find "$HOME/Downloads" -type f 2>/dev/null | wc -l | tr -d ' \n' || echo 0)
	# shellcheck disable=SC2086  # intentional word splitting or dynamic args

	# Attempt cleanup with explicit error tracking
	if ! find "$HOME/Downloads" -type f -mtime +${CLEANUP_CACHE_DAYS:-30} -delete 2>/dev/null; then
		log_warn "Some Downloads files could not be cleaned (permission denied)"
	fi

	AFTER_COUNT=$(find "$HOME/Downloads" -type f 2>/dev/null | wc -l | tr -d ' \n' || echo 0)
	CLEANED_FILES=$((BEFORE_COUNT - AFTER_COUNT))

	if ((CLEANED_FILES > 0)); then
		log_info "Cleaned $CLEANED_FILES old files from Downloads"
		((CLEANED++))
	elif ((BEFORE_COUNT > 0)); then
		log_info "No old files to clean in Downloads (or all protected)"
	fi
fi

# 3) Clean temporary directories
log_info "Cleaning temporary directories..."
for tmp_dir in "/tmp" "$HOME/.tmp" "/var/tmp"; do
	if [[ -d $tmp_dir ]]; then
		# Only clean files owned by current user to avoid permission issues
		# shellcheck disable=SC2086  # intentional word splitting or dynamic args
		if find "$tmp_dir" -user "$(whoami)" -type f -mtime +${TMP_CLEAN_DAYS:-7} -delete 2>/dev/null; then
			((CLEANED++))
		else
			log_warn "Could not clean some files in $tmp_dir (permission denied or not found)"
		fi
	fi
done

# 4) Clean trash if very full
log_info "Checking trash..."
TRASH_SIZE=$(du -sk "$HOME/.Trash" 2>/dev/null | awk '{print $1}' || echo 0)
if ((TRASH_SIZE > 1048576)); then # > 1GB
	log_warn "Trash is large ($((TRASH_SIZE / 1024)) MB), consider emptying"
fi

# 5) Clean browser caches (safe locations only)
log_info "Cleaning browser caches..."
for browser_cache in \
	"$HOME/Library/Caches/com.google.Chrome/Default/Cache" \
	"$HOME/Library/Caches/org.mozilla.firefox" \
	"$HOME/Library/Caches/com.apple.Safari"; do

	if [[ -d $browser_cache ]]; then
		# NOTE: bash-native expansion; avoids fork per iteration
		_parent="${browser_cache%/*}"
		CACHE_NAME="${_parent##*/}"
		unset _parent
		if find "$browser_cache" -type f -mtime +7 -delete 2>/dev/null; then
			((CLEANED++))
		else
			log_warn "Could not clean $CACHE_NAME cache (permission denied or browser running)"
		fi
	fi
done

# 6) System log cleanup (user-accessible only)
log_info "Cleaning old logs..."
# shellcheck disable=SC2086  # intentional word splitting or dynamic args
if [[ -d $LOG_DIR ]]; then
	find "$LOG_DIR" -type f -name "*.log" -mtime +${LOG_RETENTION_DAYS:-60} -delete 2>/dev/null || true
fi

# 7) Quick disk space check
DISK_USE=$(df -P / | awk 'NR==2 {print $5}' | tr -d '%')
log_info "Current disk usage: ${DISK_USE}%"

# 8) Clean up package manager caches
if command -v brew >/dev/null 2>&1; then
	log_info "Cleaning Homebrew cache..."
	brew cleanup --prune=7 2>/dev/null || true
	((CLEANED++))
fi

if command -v npm >/dev/null 2>&1; then
	log_info "Cleaning npm cache..."
	npm cache clean --force 2>/dev/null || true
	((CLEANED++))
fi

# Notification
if command -v terminal-notifier >/dev/null 2>&1; then
	# Always provide actionable notification to view cleanup logs
	terminal-notifier -title "Quick Cleanup" \
		-subtitle "${CLEANED_COUNT} items cleaned" \
		-message "Click for details" \
		-group "maintenance" \
		-execute "$HOME/Library/Maintenance/bin/view_logs.sh quick_cleanup" 2>/dev/null || true
elif command -v osascript >/dev/null 2>&1; then
	# Fallback to osascript
	osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title (item 2 of argv)' -e 'end run' -- "Cleaned ${CLEANED} items | Disk: ${DISK_USE}%" "Quick Cleanup" 2>/dev/null || true
fi

log_info "Quick cleanup completed: ${CLEANED} items cleaned"
echo "Quick cleanup completed successfully!"

# Clean up Trunk cache (weekly to prevent rapid accumulation)
log_info "Starting Trunk cache cleanup..."
TRUNK_CACHE_DIR="$HOME/.cache/trunk"
if [[ -d $TRUNK_CACHE_DIR ]]; then
	TRUNK_BEFORE=$(du -sk "$TRUNK_CACHE_DIR" 2>/dev/null | cut -f1 || echo "0")

	# Remove old tool binaries (safe, auto-redownloads when needed)
	find "$TRUNK_CACHE_DIR/tools" -type f -atime +14 -delete 2>/dev/null || true

	# Remove old repo caches (safe, clones fresh when needed)
	find "$TRUNK_CACHE_DIR/repos" -type d -atime +3 -exec rm -rf {} \; 2>/dev/null || true

	TRUNK_AFTER=$(du -sk "$TRUNK_CACHE_DIR" 2>/dev/null | cut -f1 || echo "0")
	TRUNK_FREED=$((TRUNK_BEFORE - TRUNK_AFTER))

	if [[ $TRUNK_FREED -gt 0 ]]; then
		TRUNK_FREED_MB=$((TRUNK_FREED / 1024))
		log_info "Trunk cleanup: freed ${TRUNK_FREED_MB} MB (before: ${TRUNK_BEFORE} KB, after: ${TRUNK_AFTER} KB)"
	else
		log_info "Trunk cache: no old files to clean"
	fi
fi

# =============================================================================
# RECURRING BLOAT CLEANUP
# =============================================================================
# Paths that drift back to multi-GB within weeks and are missed by the generic
# ~/Library/Caches sweep. All three are regenerable caches, not user data.
# Diagnosed 2026-09-17 during a disk-pressure investigation.
# -----------------------------------------------------------------------------

# 1) Wallper lock-screen render cache
# Wallper rewrites the entire cache continuously: every file was under 3 days
# old while the directory still held 80 renders / 1.9GB. An age-based rule can
# therefore never fire, so retention is by count instead -- keep the newest N
# renders (the active wallpaper plus a few recent ones) and drop the rest.
# Videos/ is the wallpaper library and is NEVER touched here.
WALLPER_CACHE="$HOME/Library/Application Support/Wallper/LockScreenCache"
if [[ -d $WALLPER_CACHE ]]; then
	log_info "Cleaning Wallper lock-screen cache..."
	WALLPER_BEFORE=$(du -sk "$WALLPER_CACHE" 2>/dev/null | cut -f1 || echo "0")

	# Newest-first listing; everything past the retention count is stale.
	WALLPER_KEEP="${WALLPER_CACHE_KEEP_COUNT:-5}"
	WALLPER_TOTAL=$(find "$WALLPER_CACHE" -type f 2>/dev/null | wc -l | tr -d " ")
	if [[ $WALLPER_TOTAL -gt $WALLPER_KEEP ]]; then
		find "$WALLPER_CACHE" -type f -print0 2>/dev/null | xargs -0 stat -f "%m %N" 2>/dev/null | sort -rn | tail -n +"$((WALLPER_KEEP + 1))" | cut -d" " -f2- | while IFS= read -r stale; do
			rm -f "$stale" 2>/dev/null || true
		done
		((CLEANED++))
	fi

	WALLPER_AFTER=$(du -sk "$WALLPER_CACHE" 2>/dev/null | cut -f1 || echo "0")
	WALLPER_FREED=$((WALLPER_BEFORE - WALLPER_AFTER))
	if [[ $WALLPER_FREED -gt 0 ]]; then
		log_info "Wallper cache: freed ${WALLPER_FREED} KB (kept newest $WALLPER_KEEP of $WALLPER_TOTAL)"
	else
		log_info "Wallper cache: nothing to trim ($WALLPER_TOTAL files, keeping $WALLPER_KEEP)"
	fi
fi

# 2) Raycast extension source maps
# Every command ships a .js.map debug artifact that is never loaded at runtime.
# 2,312 maps made up 2.56GB of a 3.5GB extensions directory. Deleting them does
# not affect extension behaviour; Raycast does not checksum installed files.
if [[ ${RAYCAST_STRIP_SOURCEMAPS:-1} -eq 1 ]]; then
	RAYCAST_EXT="$HOME/.config/raycast/extensions"
	if [[ -d $RAYCAST_EXT ]] && command -v fd >/dev/null 2>&1; then
		MAP_BEFORE=$(du -sk "$RAYCAST_EXT" 2>/dev/null | cut -f1 || echo "0")
		log_info "Stripping Raycast extension source maps..."

		# Only remove maps for extensions untouched in 7 days, so an extension
		# actively being developed or reinstalled is left alone.
		# NOTE: fd defaults to the working directory -- the search path is required.
		fd -e map -t f --changed-before "7d" . "$RAYCAST_EXT" -x rm 2>/dev/null || true

		MAP_AFTER=$(du -sk "$RAYCAST_EXT" 2>/dev/null | cut -f1 || echo "0")
		MAP_FREED=$((MAP_BEFORE - MAP_AFTER))
		if [[ $MAP_FREED -gt 0 ]]; then
			log_info "Raycast source maps: freed ${MAP_FREED} KB"
		else
			log_info "Raycast source maps: none older than 7 days"
		fi
	fi
fi

# 3) Orphaned agent/server data directories
# Removal is gated on the owning app being absent. Devin - Next and Nimbus are
# installed and their directories are deliberately left in place -- a shared
# dataFolderName between forks makes name-based inference unsafe.
if [[ -n ${ORPHAN_AGENT_APPS:-} ]]; then
	ORPHAN_TARGETS=(
		"$HOME/.windsurf-server-next:Windsurf"
		"$HOME/.windsurf-next:Windsurf"
	)
	for entry in "${ORPHAN_TARGETS[@]}"; do
		dir="${entry%%:*}"
		app="${entry##*:}"

		[[ -d $dir ]] || continue

		# Skip unless the app is confirmed absent from /Applications and ~/Applications.
		if [[ -d "/Applications/$app.app" ]] || [[ -d "$HOME/Applications/$app.app" ]]; then
			log_info "Keeping $(basename "$dir"): $app is still installed"
			continue
		fi

		ORPHAN_SIZE=$(du -sk "$dir" 2>/dev/null | cut -f1 || echo "0")
		log_info "Removing orphaned agent data: $(basename "$dir") (${ORPHAN_SIZE} KB)"
		if rm -rf "$dir" 2>/dev/null; then
			((CLEANED++))
		fi
	done
fi
