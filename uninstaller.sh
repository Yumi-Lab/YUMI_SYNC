#!/bin/bash

# Define paths for the script, the systemd service file, and the moonraker.conf file
SCRIPT_PATH="/home/pi/YUMI_SYNC/yumi_sync.py"
SERVICE_PATH="/etc/systemd/system/yumi_sync.service"
REPO_DIR="/home/pi/YUMI_SYNC_repo"
MOONRAKER_CONF="/home/pi/printer_data/config/moonraker.conf"
INSTALL_SCRIPT_PATH="/home/pi/YUMI_SYNC/install.sh"

# Stop the service if it is running
systemctl stop yumi_sync.service

# Disable the service to prevent it from starting on boot
systemctl disable yumi_sync.service

# Remove the service file from systemd
rm -f "$SERVICE_PATH"

# Remove the YUMI_SYNC repository directory
if [ -d "$REPO_DIR" ]; then
    rm -rf "$REPO_DIR"
fi

# Remove the moonraker.conf file if it exists
if [ -f "$MOONRAKER_CONF" ]; then
    rm -f "$MOONRAKER_CONF"
fi

# Optionally, uninstall dependencies (requests and netifaces)

# Uninstall requests if it was installed
if python3 -c "import requests" &>/dev/null; then
    echo "Uninstalling requests..."
    sudo pip3 uninstall -y requests
fi

# Uninstall netifaces if it was installed
if python3 -c "import netifaces" &>/dev/null; then
    echo "Uninstalling netifaces..."
    sudo apt remove -y python3-netifaces
fi

# Optionally, uninstall python3 and pip3 if they were installed only for YUMI_SYNC

# Check if python3 was installed only for YUMI_SYNC
if ! dpkg -l python3 | grep -q '^.i'; then
    echo "Uninstalling python3..."
    sudo apt remove -y python3
fi

# Check if pip3 was installed only for YUMI_SYNC
if ! dpkg -l python3-pip | grep -q '^.i'; then
    echo "Uninstalling pip3..."
    sudo apt remove -y python3-pip
fi

echo "Uninstallation completed."