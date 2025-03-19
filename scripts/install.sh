#!/bin/bash

# Update system and install dependencies
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev libffi-dev libssl-dev

# Install Python packages
pip3 install --upgrade pip
pip3 install requests netifaces python-inotify

# Create systemd service
sudo tee /etc/systemd/system/yumi-sync.service > /dev/null <<EOL
[Unit]
Description=YUMI Sync Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 ${PWD}/yumi_sync.py
Restart=always
Environment=SYNC_SERVER=https://sync.yumi-lab.com/route_testing
Environment=MONITOR_FILE=/home/pi/printer_data/config/printer.cfg
WorkingDirectory=${PWD}
User=pi

[Install]
WantedBy=multi-user.target
EOL

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable yumi-sync
sudo systemctl start yumi-sync

echo "Installation complete. Service is running."
