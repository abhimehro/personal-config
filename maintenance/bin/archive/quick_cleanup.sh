#!/usr/bin/env bash
source "${HOME}/Scripts/maintenance/common.sh"
log_file_init "quick_cleanup"

echo "⚡ QUICK SYSTEM CLEANUP"
echo "======================"
echo ""

DISK_BEFORE=$(percent_used "/")
echo "💽 Disk usage before: ${DISK_BEFORE}%"
echo ""

# Function to run commands with timeout
run_with_timeout() {
	local timeout=$1
	local cmd=$2
	local desc=$3

	echo -n "- $desc... "

	if timeout "$timeout" bash -c "$cmd" >/dev/null 2>&1; then
		echo "✅"
	else
		echo "⏰ (skipped - took too long)"
	fi
}

echo "🔧 Safe cleanups (with timeouts):"

# Quick development cache cleanup
if command -v npm >/dev/null 2>&1; then
	run_with_timeout 30 "npm cache verify" "Verifying npm cache"
fi

if command -v pip3 >/dev/null 2>&1; then
	run_with_timeout 15 "pip3 cache purge" "Purging pip cache"
fi

if command -v gem >/dev/null 2>&1; then
	run_with_timeout 30 "gem cleanup" "Cleaning gem cache"
fi

if command -v brew >/dev/null 2>&1; then
	run_with_timeout 60 "brew cleanup --prune=7" "Homebrew cleanup"
	run_with_timeout 30 "brew autoremove" "Removing unused brew packages"
fi

# Quick file cleanups
echo -n "- Clearing old temp files... "
temp_cleaned=0
for temp_dir in "${TMPDIR:-/tmp}" "/tmp"; do
	if [[ -d $temp_dir ]]; then
		old_files=$(find "$temp_dir" -type f -user "$(whoami)" -mtime +1 2>/dev/null | wc -l | tr -d ' ')
		if ((old_files > 0)); then
			find "$temp_dir" -type f -user "$(whoami)" -mtime +1 -delete 2>/dev/null || true
			((temp_cleaned += old_files))
		fi
	fi
done
echo "✅ ($temp_cleaned files)"

echo -n "- Clearing old log files... "
log_cleaned=0
if [[ -d "${HOME}/Library/Logs" ]]; then
	old_logs=$(find "${HOME}/Library/Logs" -name "*.log" -mtime +30 2>/dev/null | wc -l | tr -d ' ')
	if ((old_logs > 0)); then
		find "${HOME}/Library/Logs" -name "*.log" -mtime +30 -delete 2>/dev/null || true
		log_cleaned=$old_logs
	fi
fi
echo "✅ ($log_cleaned files)"

echo -n "- Clearing old downloads... "
downloads_cleaned=0
if [[ -d "${HOME}/Downloads" ]]; then
	old_downloads=$(find "${HOME}/Downloads" -type f -mtime +90 2>/dev/null | wc -l | tr -d ' ')
	if ((old_downloads > 0)); then
		find "${HOME}/Downloads" -type f -mtime +90 -delete 2>/dev/null || true
		downloads_cleaned=$old_downloads
	fi
fi
echo "✅ ($downloads_cleaned files)"

echo ""
echo "🔍 QUICK SYSTEM ANALYSIS"
echo "========================"

# Check disk usage after cleanup
DISK_AFTER=$(percent_used "/")
if ((DISK_BEFORE > DISK_AFTER)); then
	saved=$((DISK_BEFORE - DISK_AFTER))
	echo "✅ Freed up ${saved}% disk space!"
else
	echo "ℹ️  System was already clean"
fi
echo "💽 Current disk usage: ${DISK_AFTER}%"
echo ""

# Quick large file check (only in common locations)
echo "📊 Checking for large files (>1GB) in common locations..."
large_found=0
for search_dir in "${HOME}/Downloads" "${HOME}/Desktop" "${HOME}/Documents" "${HOME}/Movies"; do
	if [[ -d $search_dir ]]; then
		while IFS= read -r file; do
			if [[ -n $file ]]; then
				size=$(du -h "$file" 2>/dev/null | cut -f1)
				echo "  📁 $size - $file"
				((large_found++))
			fi
		done < <(find "$search_dir" -type f -size +1G 2>/dev/null | head -5)
	fi
done

if ((large_found == 0)); then
	echo "  ✅ No files >1GB found in common locations"
fi
echo ""

# Check for obvious duplicates
echo "🔄 Quick duplicate check..."
dupe_count=0
for pattern in "*copy*" "*(1)*" "*duplicate*"; do
	dupes=$(find "${HOME}/Desktop" "${HOME}/Downloads" -name "$pattern" -type f 2>/dev/null | wc -l | tr -d ' ')
	if ((dupes > 0)); then
		echo "  📋 Files matching '$pattern': $dupes"
		((dupe_count += dupes))
	fi
done

if ((dupe_count == 0)); then
	echo "  ✅ No obvious duplicates found"
fi
echo ""

# Check application remnants (quick version)
echo "🗑️  Application remnant check..."
app_remnants=0

# Quick check for obviously orphaned app support folders
if [[ -d "${HOME}/Library/Application Support" ]]; then
	while IFS= read -r -d '' dir; do
		app_name=$(basename "$dir")
		# Skip known system/common apps
		if [[ ! $app_name =~ ^(com\.|Adobe|Microsoft|Google|Apple|Dropbox|Slack|Zoom|Steam).*$ ]] &&
			[[ ! -d "/Applications/${app_name}.app" ]] &&
			[[ ! -d "/System/Applications/${app_name}.app" ]]; then
			size=$(du -sh "$dir" 2>/dev/null | cut -f1)
			echo "  📂 $app_name ($size)"
			((app_remnants++))
		fi
	done < <(find "${HOME}/Library/Application Support" -maxdepth 1 -type d -print0 2>/dev/null | head -20)
fi

if ((app_remnants == 0)); then
	echo "  ✅ No obvious application remnants found"
fi
echo ""

# iOS backup check
echo "📱 iOS backup check..."
ios_backup_dir="${HOME}/Library/Application Support/MobileSync/Backup"
if [[ -d $ios_backup_dir ]]; then
	backup_size=$(du -sh "$ios_backup_dir" 2>/dev/null | cut -f1)
	backup_count=$(find "$ios_backup_dir" -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
	echo "  📱 iOS Backups: $backup_size in $backup_count backup sets"
else
	echo "  ✅ No iOS backups found"
fi
echo ""

echo "🎯 IMMEDIATE RECOMMENDATIONS"
echo "==========================="
echo ""

if ((large_found > 0)); then
	echo "1. 📋 Review large files listed above - delete what you don't need"
fi

if ((dupe_count > 0)); then
	echo "2. 🔄 Check for duplicates in Downloads and Desktop"
fi

if ((app_remnants > 0)); then
	echo "3. 🗑️  Review application remnants:"
	echo "   • ~/Library/Application Support (folders listed above)"
	echo "   • Use AppCleaner when uninstalling apps"
fi

if [[ -d $ios_backup_dir ]]; then
	echo "4. 📱 Manage iOS backups:"
	echo "   • System Preferences > Apple ID > iCloud > Manage > Backups"
fi

echo ""
echo "⚡ NEXT STEPS"
echo "============="
echo "For deeper analysis, run:"
echo "  ~/Scripts/maintenance/deep_cleaner.sh"
echo ""
echo "For daily monitoring:"
echo "  ~/Scripts/maintenance/health_check.sh"
echo ""
echo "✅ Quick cleanup complete in $(($(date +%s) - START_TIME))s!"

log_info "Quick cleanup complete"
