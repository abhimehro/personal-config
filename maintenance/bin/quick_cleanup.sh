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

MAINT_WARNING_COUNT=0
log_warn() {
	MAINT_WARNING_COUNT=$((MAINT_WARNING_COUNT + 1))
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

# 2) Downloads: no unattended age-based deletion.
# Personal files are not cache; retention changes require separate review.
log_info "Downloads deletion disabled by containment policy; files left untouched"

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

# 9) Trunk.io cache
# Trunk caches a full toolchain per tool VERSION under tools/<tool>/<version>.
# This cache was the largest single contributor to the 2026-09 disk-pressure
# incident, so it is pruned weekly rather than monthly.
#
# Why this is version-based and not age-based: an earlier revision used
# `find -atime +14`, which can never fire. Trunk rewrites the access time of
# every cached file on each run, so nothing ever looks old -- measured on
# 2026-09-18, all 71,292 files in tools/ had an atime within 7 days while the
# directory still held 2.3 GB across 9 stale checkov versions. Age is therefore
# not a usable signal here; version count is.
#
# Safety: the version pinned in .trunk/trunk.yaml is always retained, so a
# deliberate pin (for example pinact@4.1.1, held back because plugins v1.11.0
# still emit single-dash -format) is never reaped. Only versions beyond the
# pinned one and the newest TRUNK_KEEP_VERSIONS are removed, and Trunk
# re-downloads anything it still needs.
TRUNK_CACHE_DIR="$HOME/.cache/trunk"
TRUNK_KEEP_VERSIONS="${TRUNK_KEEP_VERSIONS:-2}"
if [[ -d $TRUNK_CACHE_DIR/tools ]]; then
	log_info "Cleaning Trunk cache..."
	TRUNK_BEFORE=$(du -sk "$TRUNK_CACHE_DIR" 2>/dev/null | cut -f1 || echo "0")

	# Collect pinned versions from any trunk.yaml in the repo, so an explicit
	# pin is never treated as stale. Format: "- tool@1.2.3".
	TRUNK_PINS=""
	if [[ -f "$HOME/dev/personal-config/.trunk/trunk.yaml" ]]; then
		TRUNK_PINS=$(grep -oE '[a-z0-9-]+@[0-9][0-9a-zA-Z.-]*' \
			"$HOME/dev/personal-config/.trunk/trunk.yaml" 2>/dev/null | sort -u || true)
	fi

	TRUNK_REMOVED=0
	for tool_dir in "$TRUNK_CACHE_DIR"/tools/*/; do
		[[ -d $tool_dir ]] || continue
		tool_name=$(basename "$tool_dir")

		# Version directories only; .lock and .marker siblings are left alone.
		# bash 3.2 compatible: no mapfile/readarray (macOS /bin/bash is 3.2, and
		# launchd invokes this script as /bin/bash).
		versions=()
		while IFS= read -r v; do
			[[ -n $v ]] && versions+=("$v")
		done < <(find "$tool_dir" -maxdepth 1 -mindepth 1 -type d -exec basename {} \; 2>/dev/null | sort)

		[[ ${#versions[@]} -gt $TRUNK_KEEP_VERSIONS ]] || continue

		# Newest N by mtime, computed over the version directories.
		keep=()
		while IFS= read -r v; do
			[[ -n $v ]] && keep+=("$v")
		done < <(
			find "$tool_dir" -maxdepth 1 -mindepth 1 -type d -exec stat -f "%m %N" {} + 2>/dev/null | sort -rn | head -n "$TRUNK_KEEP_VERSIONS" | while read -r _ p; do basename "$p"; done
		)

		for v in "${versions[@]}"; do
			# Retain if it is one of the newest N.
			retain=0
			for k in "${keep[@]}"; do
				[[ $v == "$k" ]] && retain=1 && break
			done

			# Retain if explicitly pinned in trunk.yaml.
			if [[ $retain -eq 0 && -n $TRUNK_PINS ]]; then
				while IFS= read -r pin; do
					[[ -z $pin ]] && continue
					pin_tool="${pin%@*}"
					pin_ver="${pin##*@}"
					if [[ $pin_tool == "$tool_name" && $v == "$pin_ver"* ]]; then
						retain=1
						break
					fi
				done <<<"$TRUNK_PINS"
			fi

			[[ $retain -eq 1 ]] && continue

			if rm -rf "$tool_dir$v" "$tool_dir$v.lock" "$tool_dir$v.marker" 2>/dev/null; then
				TRUNK_REMOVED=$((TRUNK_REMOVED + 1))
			fi
		done
	done

	# Repo clones are cheap to recreate and Trunk re-clones on demand.
	if [[ -d $TRUNK_CACHE_DIR/repos ]]; then
		find "$TRUNK_CACHE_DIR/repos" -mindepth 1 -maxdepth 1 -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true
	fi

	TRUNK_AFTER=$(du -sk "$TRUNK_CACHE_DIR" 2>/dev/null | cut -f1 || echo "0")
	TRUNK_FREED=$((TRUNK_BEFORE - TRUNK_AFTER))
	if [[ $TRUNK_FREED -gt 0 ]]; then
		log_info "Trunk cache: removed ${TRUNK_REMOVED} stale tool version(s), freed $((TRUNK_FREED / 1024)) MB"
		((CLEANED++))
	else
		log_info "Trunk cache: clean (${TRUNK_REMOVED} stale version(s) removed)"
	fi
fi

# 10) Fish universal variables: no unattended file rewrite.
# Do not edit fish_variables or replace its recovery copy behind a live shell.
log_info "Fish variable cleanup disabled by containment policy; configuration left untouched"

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

# 3) Orphaned agent/server data: never infer disposability from app absence.
# Leave Windsurf-next data/config folders intact, regardless of config switches.
log_info "Orphan agent-data removal disabled by containment policy; directories left untouched"

# 4) Click browser: orphaned WebKit ContentRuleLists
# Click compiles its ad-block filter lists into WebKit ContentRuleList files.
# After filter updates, superseded generations are left behind under hashed
# names (ContentRuleListXXXXXXX) with no -<name> suffix, while the live lists
# keep their readable names. On 2026-09-23, 10 orphans held 221MB.
#
# Removal is gated on Click not running, so WebKit never holds the files open.
CLICK_RULE_DIR="$HOME/Library/Containers/JackBogdan.Click/Data/Library/WebKit/ContentRuleLists"
if [[ -d $CLICK_RULE_DIR ]] && ! pgrep -x Click >/dev/null 2>&1; then
	CLICK_BEFORE=$(du -sk "$CLICK_RULE_DIR" 2>/dev/null | cut -f1 || echo "0")
	log_info "Cleaning orphaned Click ContentRuleLists..."

	# Live lists carry a -<name> suffix; orphaned hashed names do not.
	find "$CLICK_RULE_DIR" -type f -depth 1 -name "ContentRuleList[!-]*" \
		! -name "*-" 2>/dev/null | while IFS= read -r orphan; do
		base=$(basename "$orphan")
		case $base in
		*-*) ;; # named (live) list, keep
		*) rm -f "$orphan" 2>/dev/null || true ;;
		esac
	done

	CLICK_AFTER=$(du -sk "$CLICK_RULE_DIR" 2>/dev/null | cut -f1 || echo "0")
	CLICK_FREED=$((CLICK_BEFORE - CLICK_AFTER))
	if [[ $CLICK_FREED -gt 0 ]]; then
		log_info "Click rule lists: freed ${CLICK_FREED} KB"
		((CLEANED++))
	else
		log_info "Click rule lists: no orphans found"
	fi
fi

# 5) Siri TTS: superseded BNNS voice-model generations
# macOS downloads neural TTS voice models into
# group.com.apple.SiriTTS/BNNSModels/<set>/. When a new generation lands, the
# previous files are NOT removed: on 2026-09-23 three generations coexisted in
# one set (722MB total, 486MB stale). Files are re-downloadable on demand, and
# no daemon holds them open between uses (sirittsd runs only while speaking).
#
# Retention is by generation: within each model family (anetec, fastspeech2,
# p2a, wavernn), keep only the newest file per family and drop older ones.
# Deletion is gated on no TTS daemon running, so a mid-speech removal cannot
# happen.
SIRI_TTS_DIR="$HOME/Library/Group Containers/group.com.apple.SiriTTS/BNNSModels"
if [[ -d $SIRI_TTS_DIR ]] && ! pgrep -x sirittsd >/dev/null 2>&1; then
	TTS_BEFORE=$(du -sk "$SIRI_TTS_DIR" 2>/dev/null | cut -f1 || echo "0")
	log_info "Cleaning superseded Siri TTS model generations..."

	# stat emits "mtime<TAB>path"; a tab delimiter is required because these
	# paths contain spaces ("Group Containers"). A space delimiter would split
	# the path and silently corrupt the keep/stale lists.
	find "$SIRI_TTS_DIR" -type f \( -name "*.bin" -o -name "*.bnns" \) -print0 2>/dev/null |
		xargs -0 stat -f "%m%t%N" 2>/dev/null |
		sort -t"	" -rn |
		awk -F"	" '
			{
				# Family + role key: everything before the UUID in the filename.
				path = $2
				file = path
				sub(/.*\//, "", file)
				key = file
				sub(/_[0-9a-f]{8}-[0-9a-f]{4}.*/, "", key)
				if (key == "") key = file
				if (!(key in newest)) { newest[key] = path; keep[path] = 1 }
			}
			END {
				for (path in keep) print path
			}' >"$TMPDIR/siri_tts_keep.$$"

	KEEP_FILE="$TMPDIR/siri_tts_keep.$$"
	find "$SIRI_TTS_DIR" -type f \( -name "*.bin" -o -name "*.bnns" \) -print0 2>/dev/null |
		xargs -0 stat -f "%m%t%N" 2>/dev/null |
		sort -t"	" -rn |
		awk -F"	" -v keepfile="$KEEP_FILE" '
			NR == FNR { keep[$1] = 1; next }
			{
				if (!($2 in keep)) print $2
			}' "$KEEP_FILE" - 2>/dev/null |
		while IFS= read -r stale; do
			rm -f "$stale" 2>/dev/null || true
		done
	rm -f "$TMPDIR/siri_tts_keep.$$"

	TTS_AFTER=$(du -sk "$SIRI_TTS_DIR" 2>/dev/null | cut -f1 || echo "0")
	TTS_FREED=$((TTS_BEFORE - TTS_AFTER))
	if [[ $TTS_FREED -gt 0 ]]; then
		log_info "Siri TTS models: freed ${TTS_FREED} KB (kept newest generation)"
		((CLEANED++))
	else
		log_info "Siri TTS models: single generation, nothing to trim"
	fi
fi

# BEGIN reviewable notification policy
# Routine automated completion stays in logs, not pop-ups.
QUICK_NOTICE="Run completed; ${CLEANED} items counted"
if ((MAINT_WARNING_COUNT > 0)); then
	QUICK_NOTICE="Completed with warnings; review quick_cleanup.log"
fi
if [[ ${AUTOMATED_RUN:-0} != "1" ]] || ((MAINT_WARNING_COUNT > 0)); then
	if command -v terminal-notifier >/dev/null 2>&1; then
		terminal-notifier -title "Quick Cleanup" \
			-subtitle "$QUICK_NOTICE" \
			-message "Click for details" \
			-group "maintenance-quick-cleanup" \
			-execute "$HOME/Library/Maintenance/bin/view_logs.sh quick_cleanup" 2>/dev/null || true
	elif command -v osascript >/dev/null 2>&1; then
		osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title (item 2 of argv)' -e 'end run' -- "$QUICK_NOTICE" "Quick Cleanup" 2>/dev/null || true
	fi
fi
# END reviewable notification policy

log_info "Quick cleanup completed: ${CLEANED} items cleaned"
echo "Quick cleanup: ${QUICK_NOTICE}"
