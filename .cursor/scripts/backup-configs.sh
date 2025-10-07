#!/bin/bash
# Automated backup of key configs with support for cloud-synced backup directory

# Set your preferred backup directory here.
# By default, this script uses a local 'backups' directory inside the repo.
# To use a cloud drive (e.g., OneDrive), set BACKUP_BASE to the absolute path
# of your cloud-synced folder or a symlink pointing to it.
#
# Example for OneDrive on Mac (symlinked in repo):
#   /Users/abhimehrotra/Documents/dev/personal-config/.cursor/backup-configs
#
# To override, set the BACKUP_BASE environment variable before running the script:
#   BACKUP_BASE="/Users/abhimehrotra/Documents/dev/personal-config/.cursor/backup-configs" ./scripts/backup-configs.sh

BACKUP_BASE="${BACKUP_BASE:-backups link}"
BACKUP_DIR="$BACKUP_BASE/auto-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup configs and scripts
rsync -av configs/ "$BACKUP_DIR/configs/"
rsync -av scripts/ "$BACKUP_DIR/scripts/"
rsync -av controld-dns-switcher/ "$BACKUP_DIR/controld-dns-switcher/"

echo "✅ Backup created: $BACKUP_DIR"

###############################################################################
# Usage: Run ./scripts/backup-configs.sh to backup the configs manually.
#
# To use a cloud drive for backups:
#   1. Set the BACKUP_BASE environment variable to your cloud-synced folder path,
#      or create a symlink named 'backups' in the repo pointing to your cloud folder.
#      Example:
#        export BACKUP_BASE="/Users/abhimehrotra/Documents/dev/personal-config/.cursor/backup-configs"
#        ./scripts/backup-configs.sh
#
#   2. Or, create a symlink:
#        ln -s /Users/abhimehrotra/Documents/dev/personal-config/.cursor/backup-configs backups link
#
# To automate backups, set up a cron job as follows:
#
# 1. Open your crontab for editing:
#      crontab -e
#
# 2. Add the following line to schedule daily backups at 2:30 AM:
#      30 2 * * * BACKUP_BASE="/Users/abhimehrotra/Documents/dev/personal-config/.cursor/backup-configs" /bin/bash /path/to/your/scripts/backup-configs.sh link
#
#    - This will run the backup every day at 2:30 AM, a time when the system is
#      likely to be idle and before the start of a typical workday.
#    - Adjust the path to match your actual script location.
#
# 3. Save and exit the editor. Your backups will now run automatically.
#
# Optimal Frequency:
#   - Daily backups (early morning, e.g., 2:30 AM) are recommended for most
#     development environments to ensure recent changes are captured without
#     excessive storage use.
#   - For highly active projects, consider increasing frequency (e.g., every 6 hours).
#
# Notes:
# - Ensure the backup directory exists and has appropriate permissions.
# - Monitor disk usage and prune old backups as needed.
#
# License:
# - This script is licensed under the MIT License.
# - Free to use and modify.
###############################################################################
