#!/bin/bash

# ==============================================================================
# service_optimizer.sh
#
# Purpose:
#   Disables non-essential macOS background services and kills unwanted widget
#   extensions to reduce system resource usage, memory consumption, and excessive
#   crash reports. This script automates the manual steps outlined in the
#   `macos-disabled-services.md` document.
#
# Requirements:
#   - Must be run with sudo privileges to manage system-level launchd services.
#
# Idempotent:
#   This script is safe to run multiple times. It checks if services are
#   already disabled before attempting to disable them again.
# ==============================================================================

set -euo pipefail

# --- Pre-flight Checks ---

if [[ "$EUID" -ne 0 ]]; then
  echo "Error: This script must be run with sudo."
  exit 1
fi

# Determine the current logged-in user's ID for GUI services.
# This is more robust than assuming UID 501.
CURRENT_UID=$(stat -f%u /dev/console)
if [[ -z "$CURRENT_UID" ]]; then
    echo "Error: Could not determine the logged-in user's ID."
    exit 1
fi

echo "--- Service Optimizer ---"
echo "Targeting services for User ID: $CURRENT_UID"
echo

# --- System-Level Services ---

# These services run at the system level and are common culprits for
# background activity and resource usage.
SYSTEM_SERVICES_TO_DISABLE=(
    "system/com.apple.chronod"           # Widget timeline manager
    "system/com.apple.duetexpertd"       # Predictive app launcher (Siri Suggestions)
    "system/com.apple.suggestd"          # Suggestions daemon
    "system/com.apple.ReportCrash.Root"  # Root-level crash reporting
)

echo "[1/3] Disabling system-level services..."
for service in "${SYSTEM_SERVICES_TO_DISABLE[@]}"; do
    # Check if the service is already disabled to ensure idempotency.
    if launchctl print-disabled "$service" | grep -q '"disabled" => true'; then
        echo "  - Already disabled: $service"
    else
        echo "  - Disabling: $service"
        launchctl disable "$service"
    fi
done
echo

# --- User-Level Services ---

# These services run at the user level (per-GUI session) and are often
# related to apps and features that are not actively in use.
USER_SERVICES_TO_DISABLE=(
    "gui/$CURRENT_UID/com.apple.ReportCrash"                               # User-level crash reporting
    "gui/$CURRENT_UID/com.apple.calendar.CalendarAgentBookmarkMigrationService" # Calendar widget services
    "gui/$CURRENT_UID/com.apple.podcasts.PodcastContentService"            # Podcasts background content fetching
    "gui/$CURRENT_UID/com.apple.proactived"                                # Proactive suggestions and predictions
    "gui/$CURRENT_UID/com.apple.peopled"                                   # People/Contacts widget backend
    "gui/$CURRENT_UID/com.apple.knowledge-agent"                           # Knowledge graph agent (powers Siri)
    "gui/$CURRENT_UID/com.apple.appstoreagent"                             # App Store background agent
    "gui/$CURRENT_UID/com.apple.commerce"                                  # App Store commerce backend
    "gui/$CURRENT_UID/com.apple.photoanalysisd"                            # Photos background analysis
    "gui/$CURRENT_UID/com.apple.photolibraryd"                             # Photos library service
)

echo "[2/3] Disabling user-level services for UID $CURRENT_UID..."
for service in "${USER_SERVICES_TO_DISABLE[@]}"; do
    if launchctl print-disabled "$service" | grep -q '"disabled" => true'; then
        echo "  - Already disabled: $service"
    else
        echo "  - Disabling: $service"
        launchctl disable "$service"
    fi
done
echo

# --- Terminate Unwanted Widget Extensions ---

# This list is based on `macos-disabled-services.md` and includes common
# Apple, Microsoft, and third-party widgets that consume memory.
WIDGETS_TO_KILL=(
    # Apple Widgets
    "CalendarWidgetExtension"
    "StocksWidget"
    "WeatherWidget"
    "NewsToday"
    "TipsWidget"
    "Home"
    "FindMy"
    "Journal"
    "Reminders"
    "Shortcuts"
    "Notes"
    "Photos"
    "World Clock"
    "People"
    "Safari"
    "Screen Time"
    "Batteries"
    "PodcastsWidget"
    # Microsoft Office Widgets
    "Word"
    "Excel"
    "PowerPoint"
    # Third-party Widgets
    "Drafts"
    "Dropover"
    "Yoink"
)

echo "[3/3] Terminating unwanted widget extensions..."
killed_count=0
for widget in "${WIDGETS_TO_KILL[@]}"; do
    # Use pkill to find and kill processes matching the widget name.
    # The -f flag matches against the full command line for better accuracy.
    # Errors are redirected to /dev/null if the process isn't running.
    if pkill -9 -f "$widget" &>/dev/null; then
        echo "  - Terminated processes matching: $widget"
        ((killed_count++))
    fi
done

if [[ "$killed_count" -eq 0 ]]; then
    echo "  - No running widget extensions from the kill list were found."
fi
echo

echo "--- Optimization Complete ---"
