#!/bin/bash

SERVICE_PATH="/etc/systemd/system/yumi_sync.service"
MOONRAKER_CONF="/home/pi/printer_data/config/moonraker.conf"

# Stop the service if it is running
sudo systemctl stop yumi_sync.service

# Disable the service to prevent it from starting on boot
sudo systemctl disable yumi_sync.service

# Remove the service file from systemd
rm -f "$SERVICE_PATH"

# Remove the YUMI_SYNC repository directory
if [ -d "/home/pi/YUMI_SYNC" ]; then
    rm -rfv "/home/pi/YUMI_SYNC"
fi

# Remove the moonraker.conf config-sync-git if it exists
sed -i '/\[include yumi_sync.cfg\]/d' "$MOONRAKER_CONF"

# Remove the monitoring_state.json file if it exists
rm -fv "${HOME}/monitoring_state.json"

echo "Uninstallation completed."
