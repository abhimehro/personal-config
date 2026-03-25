#!/usr/bin/env bash
source "${HOME}/Scripts/maintenance/common.sh"
log_file_init "execute_cleanup"

echo "🧹 EXECUTING SAFE CLEANUP"
echo "========================="
echo ""

DISK_BEFORE=$(percent_used "/")
echo "💽 Disk usage before cleanup: ${DISK_BEFORE}%"
echo ""

total_freed=0

# Function to safely remove and report
safe_remove() {
	local path="$1"
	local desc="$2"

	if [[ -d $path ]] || [[ -f $path ]]; then
		size_before=$(du -sk "$path" 2>/dev/null | cut -f1)
		echo -n "🗑️  $desc..."
		rm -rf "$path" 2>/dev/null && echo " ✅ (${size_before}KB freed)" || echo " ❌ (failed)"
		((total_freed += size_before))
	else
		echo "ℹ️  $desc: not found"
	fi
}

echo "1. Clearing browser caches (you'll need to log back in):"
safe_remove "${HOME}/Library/Caches/com.google.Chrome/Default/Cache" "Chrome cache"
safe_remove "${HOME}/Library/Caches/com.brave.Browser/Default/Cache" "Brave cache"
safe_remove "${HOME}/Library/Caches/com.microsoft.edgemac/Default/Cache" "Edge cache"
safe_remove "${HOME}/Library/Caches/com.apple.Safari/Cache.db" "Safari cache"

echo ""
echo "2. Clearing system caches:"
safe_remove "${HOME}/Library/Caches/com.apple.QuickTime/Downloads" "QuickTime downloads"
safe_remove "${HOME}/Library/Caches/CloudKit" "CloudKit cache"

echo ""
echo "3. Development cache cleanup (safe operations only):"

# Only do safe, quick operations
if command -v brew >/dev/null 2>&1; then
	echo -n "🍺 Homebrew cleanup..."
	if timeout 30 brew cleanup --prune=1 >/dev/null 2>&1; then
		echo " ✅"
	else
		echo " ⏰ (timed out)"
	fi
fi

echo ""
echo "4. Clearing temporary files:"
temp_freed=0
for temp_dir in "${TMPDIR:-/tmp}" "/tmp"; do
	if [[ -d $temp_dir ]]; then
		old_files=$(find "$temp_dir" -type f -user "$(whoami)" -mtime +0 2>/dev/null)
		if [[ -n $old_files ]]; then
			temp_size=$(echo "$old_files" | xargs du -sk 2>/dev/null | awk '{sum+=$1} END {print sum+0}')
			echo "$old_files" | xargs rm -f 2>/dev/null
			echo "🗑️  Temporary files: ✅ (${temp_size}KB freed)"
			((temp_freed += temp_size))
		fi
	fi
done

if ((temp_freed == 0)); then
	echo "ℹ️  No temporary files to clean"
fi

echo ""
echo "5. Clearing old logs:"
log_freed=0
if [[ -d "${HOME}/Library/Logs" ]]; then
	old_logs=$(find "${HOME}/Library/Logs" -name "*.log" -mtime +7 2>/dev/null)
	if [[ -n $old_logs ]]; then
		log_size=$(echo "$old_logs" | xargs du -sk 2>/dev/null | awk '{sum+=$1} END {print sum+0}')
		echo "$old_logs" | xargs rm -f 2>/dev/null
		echo "🗑️  Old log files: ✅ (${log_size}KB freed)"
		log_freed=$log_size
	fi
fi

if ((log_freed == 0)); then
	echo "ℹ️  No old log files to clean"
fi

echo ""
echo "6. System font cache refresh:"
echo -n "🔤 Refreshing font caches..."
if atsutil databases -remove >/dev/null 2>&1; then
	echo " ✅ (restart recommended for full effect)"
else
	echo " ❌ (requires admin privileges)"
fi

echo ""
echo "7. DNS cache refresh:"
echo -n "🌐 Clearing DNS cache..."
if sudo dscacheutil -flushcache >/dev/null 2>&1 && sudo killall -HUP mDNSResponder >/dev/null 2>&1; then
	echo " ✅"
else
	echo " ⏰ (requires admin privileges - run manually if needed)"
fi

DISK_AFTER=$(percent_used "/")
echo ""
echo "📊 CLEANUP RESULTS"
echo "=================="
echo "💽 Disk usage before: ${DISK_BEFORE}%"
echo "💽 Disk usage after:  ${DISK_AFTER}%"

if ((DISK_BEFORE > DISK_AFTER)); then
	saved=$((DISK_BEFORE - DISK_AFTER))
	echo "✅ Total space freed: ${saved}% of disk"
else
	echo "ℹ️  System was already quite clean"
fi

total_mb=$((total_freed / 1024))
if ((total_mb > 0)); then
	echo "📁 Files removed: ~${total_mb}MB"
fi

echo ""
echo "🎯 MANUAL REVIEW NEEDED"
echo "======================="
echo ""
echo "Large directories that need your review:"
echo "1. Zed editor (6.5GB) - ~/Library/Application Support/Zed"
echo "   • This is your code editor data - review if needed"
echo ""
echo "2. ProtonMail Bridge (5.1GB) - ~/Library/Application Support/protonmail"
echo "   • Email client data - check if you still use ProtonMail Bridge"
echo ""
echo "3. Microsoft Office (3.5GB) - ~/Library/Application Support/Microsoft"
echo "   • Office documents and cache - review for old files"
echo ""

echo "🔍 To investigate these directories:"
echo '   open ~/Library/Application\ Support/Zed'
echo '   open ~/Library/Application\ Support/protonmail'
echo '   open ~/Library/Application\ Support/Microsoft'
echo ""

echo "⚡ ADDITIONAL CLEANUP TOOLS"
echo "=========================="
echo ""
echo "For deeper cleaning, consider:"
echo "1. Monolingual - Remove unused language files"
echo "   brew install --cask monolingual"
echo ""
echo "2. DupeGuru - Find duplicate files"
echo "   brew install --cask dupeguru"
echo ""
echo "3. Manual browser profile cleanup:"
echo "   • Chrome: chrome://settings/clearBrowserData"
echo "   • Brave: brave://settings/clearBrowserData"
echo ""

log_info "Safe cleanup execution complete"
notify "Cleanup Complete" "Freed ${saved:-0}% disk space. Check large directories manually."

echo "✅ Safe cleanup complete!"
