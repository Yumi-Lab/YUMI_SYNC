#!/bin/bash

# Define paths for the script and the systemd service file
SCRIPT_PATH="/home/pi/YUMI_SYNC/yumi_sync.py"
SERVICE_PATH="/etc/systemd/system/yumi_sync.service"
REPO_URL="https://github.com/Yumi-Lab/YUMI-SYNC.git"
REPO_DIR="/home/pi/YUMI_SYNC_repo"

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

# Copy the Python script to the installation directory
cp "$REPO_DIR/yumi_sync.py" "$SCRIPT_PATH"

# Ensure the script is executable
chmod +x "$SCRIPT_PATH"

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

# Reload systemd to recognize the changes
systemctl daemon-reload

# Start the service
systemctl start yumi_sync.service

# Enable the service to start on boot
systemctl enable yumi_sync.service

echo "Installation completed. The YUMI_SYNC service is running and enabled on boot."
