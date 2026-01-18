#!/usr/bin/env bash

# Maintenance Scripts Installation
# Installs scripts to ~/Library/Maintenance and sets up launchd agents

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/Library/Maintenance"
LOG_DIR="$HOME/Library/Logs/maintenance"
LAUNCHAGENTS_DIR="$HOME/Library/LaunchAgents"

echo "🔧 Installing maintenance scripts..."

# Create directories
mkdir -p "$INSTALL_DIR/bin"
mkdir -p "$INSTALL_DIR/conf"
mkdir -p "$LOG_DIR"
mkdir -p "$LAUNCHAGENTS_DIR"

# Copy scripts
echo "📦 Copying scripts to $INSTALL_DIR..."
cp -r "$SCRIPT_DIR/bin/"* "$INSTALL_DIR/bin/"
chmod +x "$INSTALL_DIR/bin/"*.sh

# Copy configuration if exists
if [ -d "$SCRIPT_DIR/conf" ]; then
    cp -r "$SCRIPT_DIR/conf/"* "$INSTALL_DIR/conf/" 2>/dev/null || true
fi

# Generate plist files with correct paths
echo "📝 Generating launchd plist files..."

# Brew Maintenance (Daily at 10 AM)
cat > "$LAUNCHAGENTS_DIR/com.abhimehrotra.maintenance.brew.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.abhimehrotra.maintenance.brew</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>MAINTENANCE_HOME</key>
        <string>$INSTALL_DIR</string>
        <key>HOMEBREW_NO_ENV_HINTS</key>
        <string>1</string>
        <key>AUTOMATED_RUN</key>
        <string>1</string>
    </dict>
    
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$INSTALL_DIR/bin/brew_maintenance.sh</string>
    </array>
    
    <key>StandardOutPath</key>
    <string>$LOG_DIR/brew_maintenance.out</string>
    
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/brew_maintenance.err</string>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>10</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>RunAtLoad</key>
    <false/>
    
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
EOF

# Health Check (Daily at 8:30 AM)
cat > "$LAUNCHAGENTS_DIR/com.abhimehrotra.maintenance.healthcheck.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.abhimehrotra.maintenance.healthcheck</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>MAINTENANCE_HOME</key>
        <string>$INSTALL_DIR</string>
        <key>AUTOMATED_RUN</key>
        <string>1</string>
    </dict>
    
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$INSTALL_DIR/bin/health_check.sh</string>
    </array>
    
    <key>StandardOutPath</key>
    <string>$LOG_DIR/health_check.out</string>
    
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/health_check.err</string>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>
    
    <key>RunAtLoad</key>
    <false/>
    
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
EOF

# System Cleanup (Daily at 9 AM)
cat > "$LAUNCHAGENTS_DIR/com.abhimehrotra.maintenance.systemcleanup.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.abhimehrotra.maintenance.systemcleanup</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>MAINTENANCE_HOME</key>
        <string>$INSTALL_DIR</string>
        <key>AUTOMATED_RUN</key>
        <string>1</string>
    </dict>
    
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$INSTALL_DIR/bin/system_cleanup.sh</string>
    </array>
    
    <key>StandardOutPath</key>
    <string>$LOG_DIR/system_cleanup.out</string>
    
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/system_cleanup.err</string>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>RunAtLoad</key>
    <false/>
    
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
EOF

# Weekly Maintenance (Mondays at 9 AM)
cat > "$LAUNCHAGENTS_DIR/com.abhimehrotra.maintenance.weekly.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.abhimehrotra.maintenance.weekly</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>MAINTENANCE_HOME</key>
        <string>$INSTALL_DIR</string>
        <key>AUTOMATED_RUN</key>
        <string>1</string>
    </dict>
    
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$INSTALL_DIR/bin/weekly_maintenance.sh</string>
    </array>
    
    <key>StandardOutPath</key>
    <string>$LOG_DIR/maintenance_weekly.out</string>
    
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/maintenance_weekly.err</string>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>1</integer>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>RunAtLoad</key>
    <false/>
    
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
EOF

# Monthly Maintenance (1st of month at 6 AM)
cat > "$LAUNCHAGENTS_DIR/com.abhimehrotra.maintenance.monthly.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.abhimehrotra.maintenance.monthly</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>MAINTENANCE_HOME</key>
        <string>$INSTALL_DIR</string>
        <key>AUTOMATED_RUN</key>
        <string>1</string>
    </dict>
    
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$INSTALL_DIR/bin/monthly_maintenance.sh</string>
    </array>
    
    <key>StandardOutPath</key>
    <string>$LOG_DIR/maintenance_monthly.out</string>
    
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/maintenance_monthly.err</string>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Day</key>
        <integer>1</integer>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>RunAtLoad</key>
    <false/>
    
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
EOF

# Service Monitor (Daily at 8:35 AM)
cat > "$LAUNCHAGENTS_DIR/com.abhimehrotra.maintenance.servicemonitor.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.abhimehrotra.maintenance.servicemonitor</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>MAINTENANCE_HOME</key>
        <string>$INSTALL_DIR</string>
        <key>AUTOMATED_RUN</key>
        <string>1</string>
    </dict>
    
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$INSTALL_DIR/bin/service_monitor.sh</string>
    </array>
    
    <key>StandardOutPath</key>
    <string>$LOG_DIR/servicemonitor-stdout.log</string>
    
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/servicemonitor-stderr.log</string>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>35</integer>
    </dict>
    
    <key>RunAtLoad</key>
    <false/>
    
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
EOF

# Screen Capture Nag Remover (Daily at 10:00 AM)
# Note: Requires Full Disk Access for /bin/bash to modify TCC database
cat > "$LAUNCHAGENTS_DIR/com.abhimehrotra.maintenance.screencapture-nag-remover.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.abhimehrotra.maintenance.screencapture-nag-remover</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>MAINTENANCE_HOME</key>
        <string>$INSTALL_DIR</string>
    </dict>
    
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$INSTALL_DIR/bin/screencapture_nag_remover.sh</string>
    </array>
    
    <key>StandardOutPath</key>
    <string>$LOG_DIR/screencapture_nag_remover.out</string>
    
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/screencapture_nag_remover.err</string>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>10</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF

# Google Drive Home Backup (Daily at 3:15 AM - Light Mode)
# Skips weekends automatically via script logic to avoid gaming interference
cat > "$LAUNCHAGENTS_DIR/com.abhimehrotra.maintenance.googledrivebackup.light.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.abhimehrotra.maintenance.googledrivebackup.light</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>MAINTENANCE_HOME</key>
        <string>$INSTALL_DIR</string>
        <key>AUTOMATED_RUN</key>
        <string>1</string>
    </dict>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$INSTALL_DIR/bin/google_drive_backup.sh</string>
        <string>--run</string>
        <string>--light</string>
        <string>--no-delete</string>
    </array>

    <key>StandardOutPath</key>
    <string>$LOG_DIR/googledrive_backup_light.out</string>

    <key>StandardErrorPath</key>
    <string>$LOG_DIR/googledrive_backup_light.err</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>15</integer>
    </dict>

    <key>RunAtLoad</key>
    <false/>

    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
EOF

# Google Drive Full Backup (Weekly - Monday at 4:00 AM)
# Runs full backup once a week
cat > "$LAUNCHAGENTS_DIR/com.abhimehrotra.maintenance.googledrivebackup.full.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.abhimehrotra.maintenance.googledrivebackup.full</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>MAINTENANCE_HOME</key>
        <string>$INSTALL_DIR</string>
        <key>AUTOMATED_RUN</key>
        <string>1</string>
        <key>FORCE_RUN</key>
        <string>1</string>
    </dict>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$INSTALL_DIR/bin/google_drive_backup.sh</string>
        <string>--run</string>
        <string>--full</string>
        <string>--no-delete</string>
    </array>

    <key>StandardOutPath</key>
    <string>$LOG_DIR/googledrive_backup_full.out</string>

    <key>StandardErrorPath</key>
    <string>$LOG_DIR/googledrive_backup_full.err</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>1</integer>
        <key>Hour</key>
        <integer>4</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>RunAtLoad</key>
    <false/>

    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
EOF

# Unload old agents (ignore errors)
echo "🔄 Unloading old agents..."
for plist in "$LAUNCHAGENTS_DIR"/com.abhimehrotra.maintenance.*.plist "$LAUNCHAGENTS_DIR"/com.user.maintenance.*.plist; do
    [ -f "$plist" ] || continue
    launchctl unload "$plist" 2>/dev/null || true
done

# Load new agents
echo "✅ Loading new agents..."
for plist in "$LAUNCHAGENTS_DIR"/com.abhimehrotra.maintenance.*.plist; do
    [ -f "$plist" ] || continue
    launchctl load "$plist" 2>&1 || echo "⚠️  Warning: Failed to load $(basename "$plist")"
done

echo ""
echo "✨ Installation complete!"
echo ""
echo "Installed scripts to: $INSTALL_DIR/bin/"
echo "Logs will be written to: $LOG_DIR/"
echo ""
echo "Scheduled maintenance tasks:"
echo "  • Health Check: Daily at 8:30 AM"
echo "  • System Cleanup: Daily at 9:00 AM"
echo "  • Brew Maintenance: Daily at 10:00 AM"
echo "  • Screen Capture Nag Remover: Daily at 10:00 AM"
echo "  • Google Drive Backup (Light): Daily at 3:15 AM (Tue-Sun)"
echo "  • Google Drive Backup (Full): Monday at 4:00 AM"
echo "  • Weekly Maintenance: Mondays at 9:00 AM"
echo "  • Monthly Maintenance: 1st of month at 6:00 AM"
echo ""
echo "To test a script manually:"
echo "  bash $INSTALL_DIR/bin/brew_maintenance.sh"
echo ""
echo "To view logs:"
echo "  tail -f $LOG_DIR/brew_maintenance.log"
echo ""
echo "To check agent status:"
echo "  launchctl list | grep maintenance"
