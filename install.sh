#!/bin/bash

# Define paths for the script, the systemd service file, and the moonraker.conf file
SCRIPT_PATH="/home/pi/YUMI_SYNC/yumi_sync.py"
SERVICE_PATH="/etc/systemd/system/yumi_sync.service"
REPO_URL="https://github.com/Yumi-Lab/YUMI-SYNC.git"
REPO_DIR="/home/pi/YUMI_SYNC_repo"
MOONRAKER_CONF="/etc/moonraker.conf"
INSTALL_SCRIPT_PATH="/home/pi/YUMI_SYNC/install.sh"

# Check if the installation directory exists, if not, create it
if [ ! -d "/home/pi/YUMI_SYNC" ]; then
    mkdir -p /home/pi/YUMI_SYNC
fi

# Clone or update the repository to the latest version
if [ ! -d "$REPO_DIR" ]; then
    git clone "$REPO_URL" "$REPO_DIR"
else
    git -C "$REPO_DIR" pull
fi

# Ensure the script Python is executable
chmod +x "$SCRIPT_PATH"

# Check if python3 is installed, if not, install it
if ! command -v python3 &>/dev/null; then
    echo "Installing python3..."
    sudo apt update
    sudo apt install -y python3
fi

# Check if pip3 is installed, if not, install it
if ! command -v pip3 &>/dev/null; then
    echo "Installing pip3..."
    sudo apt update
    sudo apt install -y python3-pip
fi

# Check if requests is installed, if not, install it
if ! python3 -c "import requests" &>/dev/null; then
    echo "Installing requests..."
    sudo pip3 install requests
fi

# Check if netifaces is installed, if not, install it
if ! python3 -c "import netifaces" &>/dev/null; then
    echo "Installing netifaces..."
    sudo apt update
    sudo apt install -y python3-netifaces
fi

# Create the systemd service file
cat > "$SERVICE_PATH" <<EOL
[Unit]
Description=Yumi Sync Service

[Service]
ExecStart=/usr/bin/python3 $SCRIPT_PATH
WorkingDirectory=/home/pi/YUMI_SYNC
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOL

# Check if moonraker.conf exists, if not, create it and add the content
if [ ! -f "$MOONRAKER_CONF" ]; then
    cat > "$MOONRAKER_CONF" <<EOL
[update_manager Yumi_Sync]
type: git_repo
path: ~/YUMI_SYNC
origin: https://github.com/Yumi-Lab/YUMI_SYNC.git
primary_branch: main
managed_services: yumi_sync
install_script: $INSTALL_SCRIPT_PATH
EOL
fi

# Reload systemd to recognize the changes
systemctl daemon-reload

# Start the service
systemctl start yumi_sync.service

# Enable the service to start on boot
systemctl enable yumi_sync.service

echo "Installation completed. The YUMI_SYNC service is running and enabled on boot."
