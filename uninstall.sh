#!/bin/bash

# Script and service file paths
SCRIPT_PATH="/opt/YUMI_SYNC/yumi_sync.py"
SERVICE_PATH="/etc/systemd/system/yumi_sync.service"

# Stop the service if it's running
systemctl stop yumi_sync

# Disable the service to prevent it from starting at boot
systemctl disable yumi_sync

# Remove the service file
rm -f "$SERVICE_PATH"

# Reload systemd to apply changes
systemctl daemon-reload

# Remove the script directory and its contents
rm -rf "/opt/YUMI_SYNC"

echo "Uninstallation completed. The service and script have been removed."
