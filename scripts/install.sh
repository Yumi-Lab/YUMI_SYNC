#!/bin/bash

#install python-inotify
sudo apt update
sudo apt install python3-inotify -y

# Create virtual environment
VENV_DIR="${PWD}/venv"
python3 -m venv ${VENV_DIR}
source ${VENV_DIR}/bin/activate

# Install Python packages in venv
pip install --upgrade pip
pip install requests netifaces #python-inotify




# Create systemd service
sudo tee /etc/systemd/system/yumi-sync.service > /dev/null <<EOL
[Unit]
Description=YUMI Sync Service
After=network.target

[Service]
ExecStart=${VENV_DIR}/bin/python ${PWD}/yumi_sync.py
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
