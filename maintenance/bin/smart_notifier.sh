#!/usr/bin/env bash

# Smart Notification & Alert System
# Provides intelligent notifications with system insights and actionable recommendations
set -eo pipefail

# Configuration
LOG_DIR="$HOME/Library/Logs/maintenance"
NOTIFICATION_LOG="$LOG_DIR/notifications.log"
NOTIFICATION_CONFIG="$LOG_DIR/notification_config.json"
NOTIFICATION_HISTORY="$LOG_DIR/notification_history.jsonl"

mkdir -p "$LOG_DIR"

# Initialize notification configuration
if [[ ! -f "$NOTIFICATION_CONFIG" ]]; then
    cat > "$NOTIFICATION_CONFIG" << 'EOF'
{
  "enabled": true,
  "sound": true,
  "quiet_hours": {
    "enabled": true,
    "start": "22:00",
    "end": "08:00"
  },
  "priority_levels": {
    "critical": {
      "always_notify": true,
      "sound": "Basso",
      "subtitle": "Critical Alert"
    },
    "warning": {
      "always_notify": false,
      "sound": "default",
      "subtitle": "System Warning"
    },
    "info": {
      "always_notify": false,
      "sound": "none",
      "subtitle": "System Info"
    },
    "success": {
      "always_notify": false,
      "sound": "none",
      "subtitle": "Task Completed"
    }
  },
  "rate_limiting": {
    "enabled": true,
    "max_per_hour": 10,
    "cooldown_minutes": 15
  }
}
EOF
fi

# Logging function
notify_log() {
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$timestamp [NOTIFIER] $*" | tee -a "$NOTIFICATION_LOG"
}

# Check if we're in quiet hours
is_quiet_hours() {
    if ! command -v jq >/dev/null 2>&1; then
        return 1
    fi
    
    local quiet_enabled=$(jq -r '.quiet_hours.enabled // false' "$NOTIFICATION_CONFIG")
    if [[ "$quiet_enabled" != "true" ]]; then
        return 1
    fi
    
    local current_time=$(date +%H:%M)
    local start_time=$(jq -r '.quiet_hours.start // "22:00"' "$NOTIFICATION_CONFIG")
    local end_time=$(jq -r '.quiet_hours.end // "08:00"' "$NOTIFICATION_CONFIG")
    
    # Convert times to minutes for comparison
    local current_minutes=$(date -j -f "%H:%M" "$current_time" "+%H * 60 + %M" 2>/dev/null | bc 2>/dev/null || echo "0")
    local start_minutes=$(date -j -f "%H:%M" "$start_time" "+%H * 60 + %M" 2>/dev/null | bc 2>/dev/null || echo "1320")
    local end_minutes=$(date -j -f "%H:%M" "$end_time" "+%H * 60 + %M" 2>/dev/null | bc 2>/dev/null || echo "480")
    
    # Handle overnight quiet hours
    if [[ $start_minutes -gt $end_minutes ]]; then
        # Quiet hours span midnight
        if [[ $current_minutes -ge $start_minutes ]] || [[ $current_minutes -le $end_minutes ]]; then
            return 0
        fi
    else
        # Normal quiet hours
        if [[ $current_minutes -ge $start_minutes ]] && [[ $current_minutes -le $end_minutes ]]; then
            return 0
        fi
    fi
    
    return 1
}

# Check rate limiting
should_rate_limit() {
    local priority="$1"
    
    if ! command -v jq >/dev/null 2>&1; then
        return 1
    fi
    
    local rate_enabled=$(jq -r '.rate_limiting.enabled // false' "$NOTIFICATION_CONFIG")
    if [[ "$rate_enabled" != "true" ]]; then
        return 1
    fi
    
    # Always allow critical notifications
    if [[ "$priority" == "critical" ]]; then
        return 1
    fi
    
    local max_per_hour=$(jq -r '.rate_limiting.max_per_hour // 10' "$NOTIFICATION_CONFIG")
    local current_hour=$(date +%Y%m%d%H)
    
    # Count notifications in the last hour
    local notifications_this_hour=0
    if [[ -f "$NOTIFICATION_HISTORY" ]]; then
        notifications_this_hour=$(grep "$current_hour" "$NOTIFICATION_HISTORY" 2>/dev/null | wc -l | tr -d ' ')
    fi
    
    if [[ ${notifications_this_hour:-0} -ge $max_per_hour ]]; then
        notify_log "Rate limiting active: $notifications_this_hour/$max_per_hour notifications this hour"
        return 0
    fi
    
    return 1
}

# Record notification in history
record_notification() {
    local priority="$1"
    local title="$2"
    local message="$3"
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    local hour_key="$(date +%Y%m%d%H)"
    
    if command -v jq >/dev/null 2>&1; then
        echo "{\"timestamp\":\"$timestamp\",\"hour\":\"$hour_key\",\"priority\":\"$priority\",\"title\":\"$title\",\"message\":\"$message\"}" >> "$NOTIFICATION_HISTORY"
    fi
}

# Enhanced notification function
smart_notify() {
    local priority="${1:-info}" # critical, warning, info, success
    local title="$2"
    local message="$3"
    local action="${4:-}"  # Optional action button
    local sound_override="${5:-}"
    
    # Validate inputs
    if [[ -z "$title" ]] || [[ -z "$message" ]]; then
        notify_log "ERROR: Title and message are required for notifications"
        return 1
    fi
    
    # Check if notifications are enabled
    local notifications_enabled=true
    if command -v jq >/dev/null 2>&1; then
        notifications_enabled=$(jq -r '.enabled // true' "$NOTIFICATION_CONFIG")
    fi
    
    if [[ "$notifications_enabled" != "true" ]]; then
        notify_log "Notifications disabled - skipping: $title"
        return 0
    fi
    
    # Check quiet hours and rate limiting
    local skip_notification=false
    
    if is_quiet_hours; then
        local always_notify=$(jq -r ".priority_levels.$priority.always_notify // false" "$NOTIFICATION_CONFIG" 2>/dev/null)
        if [[ "$always_notify" != "true" ]]; then
            notify_log "Quiet hours active - skipping notification: $title"
            skip_notification=true
        fi
    fi
    
    if should_rate_limit "$priority"; then
        skip_notification=true
    fi
    
    # Record notification even if skipped
    record_notification "$priority" "$title" "$message"
    
    if [[ "$skip_notification" == "true" ]]; then
        return 0
    fi
    
    # Get priority-specific settings
    local subtitle="System Notification"
    local sound="default"
    
    if command -v jq >/dev/null 2>&1; then
        subtitle=$(jq -r ".priority_levels.$priority.subtitle // \"System Notification\"" "$NOTIFICATION_CONFIG")
        sound=$(jq -r ".priority_levels.$priority.sound // \"default\"" "$NOTIFICATION_CONFIG")
    fi
    
    # Override sound if specified
    if [[ -n "$sound_override" ]]; then
        sound="$sound_override"
    fi
    
    # Build notification command
    local notify_cmd="osascript -e \"display notification \\\"$message\\\" with title \\\"$title\\\" subtitle \\\"$subtitle\\\""
    
    # Add sound if not 'none'
    if [[ "$sound" != "none" ]]; then
        notify_cmd+=" sound name \\\"$sound\\\""
    fi
    
    # Add action button if specified
    if [[ -n "$action" ]]; then
        notify_cmd+=" buttons {\\\"$action\\\", \\\"OK\\\"} default button \\\"OK\\\""
    fi
    
    notify_cmd+="\""
    
    # Send notification
    if command -v osascript >/dev/null 2>&1; then
        eval "$notify_cmd" 2>/dev/null || notify_log "Failed to send notification: $title"
        notify_log "Sent notification [$priority]: $title - $message"
    else
        notify_log "osascript not available - notification: $title - $message"
    fi
}

# System status notification with insights
system_status_notification() {
    local health_status="${1:-unknown}"
    local performance_score="${2:-0}"
    local warnings="${3:-0}"
    local disk_usage="${4:-0}"
    local memory_free="${5:-0}"
    
    local priority="info"
    local title="System Status Report"
    local insights=""
    
    # Determine priority based on system state
    if [[ "$health_status" == "critical" ]] || [[ ${performance_score:-0} -lt 50 ]] || [[ ${warnings:-0} -gt 3 ]]; then
        priority="critical"
        title="🚨 Critical System Alert"
    elif [[ "$health_status" == "warning" ]] || [[ ${performance_score:-0} -lt 70 ]] || [[ ${warnings:-0} -gt 1 ]]; then
        priority="warning"
        title="⚠️ System Warning"
    else
        priority="success"
        title="✅ System Healthy"
    fi
    
    # Generate insights
    if [[ ${disk_usage:-0} -gt 85 ]]; then
        insights+="• Disk usage is high (${disk_usage}%)\n"
    fi
    
    if [[ ${memory_free:-1000} -lt 500 ]]; then
        insights+="• Low memory available (${memory_free}MB)\n"
    fi
    
    if [[ ${warnings:-0} -gt 0 ]]; then
        insights+="• ${warnings} system warnings detected\n"
    fi
    
    # Create rich message
    local message="Health: $health_status | Performance: ${performance_score}/100"
    if [[ -n "$insights" ]]; then
        message+="\n\nInsights:\n$insights"
    fi
    
    smart_notify "$priority" "$title" "$message"
}

# Maintenance task completion notification
task_completion_notification() {
    local task_name="$1"
    local status="${2:-completed}"  # completed, failed, partial
    local details="${3:-}"
    local duration="${4:-}"
    local items_processed="${5:-0}"
    local space_saved="${6:-0}"
    
    local priority="success"
    local title="✅ $task_name Completed"
    local emoji="✅"
    
    case "$status" in
        "failed")
            priority="warning"
            title="❌ $task_name Failed"
            emoji="❌"
            ;;
        "partial")
            priority="warning"
            title="⚠️ $task_name Completed with Issues"
            emoji="⚠️"
            ;;
        "completed")
            priority="success"
            title="✅ $task_name Completed"
            emoji="✅"
            ;;
    esac
    
    local message="Status: $status"
    
    if [[ -n "$duration" ]]; then
        message+=" | Duration: $duration"
    fi
    
    if [[ ${items_processed:-0} -gt 0 ]]; then
        message+=" | Items: $items_processed"
    fi
    
    if [[ ${space_saved:-0} -gt 0 ]]; then
        message+=" | Space saved: ${space_saved}MB"
    fi
    
    if [[ -n "$details" ]]; then
        message+="\n\n$details"
    fi
    
    smart_notify "$priority" "$title" "$message"
}

# Trend analysis notification
trend_notification() {
    local metric="$1"
    local current_value="$2"
    local trend="${3:-stable}"  # improving, degrading, stable
    local change_percent="${4:-0}"
    
    local priority="info"
    local title="📊 System Trend Alert"
    
    case "$trend" in
        "improving")
            priority="info"
            title="📈 System Improving"
            ;;
        "degrading")
            if [[ ${change_percent:-0} -gt 20 ]]; then
                priority="warning"
                title="📉 Performance Degradation"
            else
                priority="info"
                title="📉 System Trend"
            fi
            ;;
        "stable")
            priority="info"
            title="📊 System Stable"
            ;;
    esac
    
    local message="$metric: $current_value (${change_percent}% change)"
    
    # Only notify for significant trends
    if [[ ${change_percent:-0} -gt 10 ]] || [[ "$trend" == "degrading" ]]; then
        smart_notify "$priority" "$title" "$message"
    fi
}

# Security alert notification
security_notification() {
    local alert_type="$1"
    local description="$2"
    local severity="${3:-medium}"  # low, medium, high, critical
    
    local priority="warning"
    local title="🔒 Security Alert"
    
    case "$severity" in
        "critical")
            priority="critical"
            title="🚨 Critical Security Alert"
            ;;
        "high")
            priority="warning"
            title="⚠️ Security Warning"
            ;;
        "medium")
            priority="info"
            title="🔒 Security Notice"
            ;;
        "low")
            priority="info"
            title="🔐 Security Info"
            ;;
    esac
    
    local message="Type: $alert_type\n$description"
    
    smart_notify "$priority" "$title" "$message" "View Logs"
}

# Predictive maintenance notification
predictive_notification() {
    local prediction="$1"
    local confidence="${2:-0}"
    local recommended_action="$3"
    local timeline="${4:-}"
    
    local priority="info"
    local title="🔮 Predictive Maintenance"
    
    if [[ ${confidence:-0} -gt 80 ]]; then
        priority="warning"
        title="⚡ Maintenance Recommended"
    fi
    
    local message="Prediction: $prediction"
    
    if [[ ${confidence:-0} -gt 0 ]]; then
        message+=" (${confidence}% confidence)"
    fi
    
    if [[ -n "$timeline" ]]; then
        message+="\nTimeline: $timeline"
    fi
    
    if [[ -n "$recommended_action" ]]; then
        message+="\n\nRecommended: $recommended_action"
    fi
    
    smart_notify "$priority" "$title" "$message" "Schedule"
}

# Batch notification for summaries
batch_summary_notification() {
    local period="$1"  # daily, weekly, monthly
    local total_tasks="$2"
    local successful_tasks="$3"
    local failed_tasks="$4"
    local total_space_saved="$5"
    local avg_performance="$6"
    
    local priority="info"
    local title="📋 ${period^} Summary"
    local emoji="📋"
    
    if [[ ${failed_tasks:-0} -gt 0 ]]; then
        priority="warning"
        title="⚠️ ${period^} Summary (Issues Detected)"
        emoji="⚠️"
    else
        priority="success"
        title="✅ ${period^} Summary"
        emoji="✅"
    fi
    
    local success_rate=0
    if [[ ${total_tasks:-0} -gt 0 ]]; then
        success_rate=$(( (successful_tasks * 100) / total_tasks ))
    fi
    
    local message="Tasks: $successful_tasks/$total_tasks completed (${success_rate}%)"
    
    if [[ ${total_space_saved:-0} -gt 0 ]]; then
        message+=" | Space saved: ${total_space_saved}MB"
    fi
    
    if [[ ${avg_performance:-0} -gt 0 ]]; then
        message+=" | Avg performance: ${avg_performance}/100"
    fi
    
    smart_notify "$priority" "$title" "$message"
}

# Configuration management
update_notification_config() {
    local key="$1"
    local value="$2"
    
    if command -v jq >/dev/null 2>&1; then
        local temp_file=$(mktemp)
        jq --arg key "$key" --arg value "$value" \
           'setpath($key | split("."); $value)' \
           "$NOTIFICATION_CONFIG" > "$temp_file" && mv "$temp_file" "$NOTIFICATION_CONFIG"
        notify_log "Updated configuration: $key = $value"
    fi
}

# Test notification system
test_notifications() {
    notify_log "Testing notification system"
    
    smart_notify "info" "Test Info" "This is a test info notification"
    sleep 2
    
    smart_notify "success" "Test Success" "This is a test success notification"
    sleep 2
    
    smart_notify "warning" "Test Warning" "This is a test warning notification"
    sleep 2
    
    smart_notify "critical" "Test Critical" "This is a test critical notification"
    
    notify_log "Notification test completed"
}

# Export functions for use in other scripts
export -f smart_notify
export -f system_status_notification
export -f task_completion_notification
export -f trend_notification
export -f security_notification
export -f predictive_notification
export -f batch_summary_notification

notify_log "Smart notification system loaded successfully"

# If script is run directly, show usage
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Smart Notification System"
    echo "Usage: source this script to load functions, or:"
    echo "  $0 test                    # Run notification tests"
    echo "  $0 status <health> <perf>  # Send system status notification"
    
    case "${1:-}" in
        "test")
            test_notifications
            ;;
        "status")
            system_status_notification "${2:-healthy}" "${3:-85}" "${4:-0}"
            ;;
        *)
            echo "For integration, source this script in your maintenance scripts:"
            echo "  source /path/to/smart_notifier.sh"
            echo "  smart_notify 'success' 'Task Complete' 'Details here'"
            ;;
    esac
fi