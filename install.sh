#!/bin/bash

<<<<<<< HEAD
# Define paths for the script and the systemd service file
SCRIPT_PATH="/home/pi/YUMI_SYNC/yumi_sync.py"
SERVICE_PATH="/etc/systemd/system/yumi_sync.service"
REPO_URL="https://github.com/Yumi-Lab/YUMI-SYNC.git"
REPO_DIR="/home/pi/YUMI_SYNC_repo"
=======
# Script and service file paths
SCRIPT_PATH="/opt/YUMI_SYNC/yumi_sync.py"
SERVICE_PATH="/etc/systemd/system/yumi_sync.service"
>>>>>>> 919e9d3b6767d0fceb4a6e035340d2b974bc4ed4

# Install Python module requests using apt
apt install -y python3-requests

# Check if the installation directory exists, if not, create it
<<<<<<< HEAD
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
=======
if [ ! -d "/opt/YUMI_SYNC" ]; then
    mkdir -p /opt/YUMI_SYNC
fi

# Create the Python script
cat << 'EOF' > "$SCRIPT_PATH"
import os
import time
import requests
import hashlib
import json
from datetime import datetime, timedelta

file_to_monitor = '/home/pi/printer_data/config/printer.cfg'
state_file_path = '/home/pi/monitoring_state.json'
server_url = "http://adb528.online-server.cloud/route_testing"

previous_hash = None

def calculate_file_hash(file_path):
    try:
        with open(file_path, 'rb') as file:
            return hashlib.md5(file.read()).hexdigest()
    except Exception as e:
        print(f"Error calculating file hash: {e}")
        return None

def send_file_to_server(file_path, timestamp):
    try:
        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file)}
            data = {
                'timestamp': timestamp
            }
            response = requests.post(server_url, data=data, files=files)

            if response.status_code == 200:
                print("Data successfully sent to server.")
            else:
                print(f"Error sending data to the server. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending data to the server: {e}")

def load_previous_hash():
    try:
        with open(state_file_path, 'r') as state_file:
            return state_file.read().strip()
    except FileNotFoundError:
        return None

def save_current_hash(current_hash):
    with open(state_file_path, 'w') as state_file:
        state_file.write(current_hash)

def load_last_sent_date():
    try:
        with open(state_file_path, 'r') as state_file:
            state_data = json.load(state_file)
            return state_data.get('last_sent_date')
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def save_last_sent_date(date):
    try:
        with open(state_file_path, 'r') as state_file:
            state_data = json.load(state_file)
    except (FileNotFoundError, json.JSONDecodeError):
        state_data = {}
    
    state_data['last_sent_date'] = date

    with open(state_file_path, 'w') as state_file:
        json.dump(state_data, state_file)

while True:
    try:
        current_hash = calculate_file_hash(file_to_monitor)
        if current_hash is not None and current_hash != previous_hash:
            print("The file has changed. Sending data to the server...")
            timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
            send_file_to_server(file_to_monitor, timestamp)
            save_current_hash(current_hash)
        
        previous_hash = current_hash

        last_sent_date = load_last_sent_date()
        if last_sent_date is None or (datetime.now() - datetime.strptime(last_sent_date, "%Y-%m-%d")).days >= 30:
            print("Sending the file as it has been 30 days or more...")
            timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
            send_file_to_server(file_to_monitor, timestamp)
            save_current_hash(current_hash)
            save_last_sent_date(time.strftime("%Y-%m-%d"))

        time.sleep(5)
    except KeyboardInterrupt:
        print("Monitoring stopped.")
        break
    except Exception as e:
        print(f"Error in monitoring: {e}")
EOF
>>>>>>> 919e9d3b6767d0fceb4a6e035340d2b974bc4ed4

# Create the systemd service file
cat > "$SERVICE_PATH" <<EOL
[Unit]
Description=Yumi Sync Service

[Service]
ExecStart=/usr/bin/python3 $SCRIPT_PATH
<<<<<<< HEAD
WorkingDirectory=/home/pi/YUMI_SYNC
=======
WorkingDirectory=/opt/YUMI_SYNC
>>>>>>> 919e9d3b6767d0fceb4a6e035340d2b974bc4ed4
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOL

<<<<<<< HEAD
# Reload systemd to recognize the changes
systemctl daemon-reload

# Start the service
systemctl start yumi_sync.service

# Enable the service to start on boot
<<<<<<< HEAD:install.sh
systemctl enable yumi_sync.service

echo "Installation completed. The YUMI_SYNC service is running and enabled on boot."
=======
=======
# Reload systemd to recognize changes
systemctl daemon-reload

# Start the service
systemctl start yumi_sync

# Enable the service to start on boot
systemctl enable yumi_sync

echo "Installation completed. Server is running."
>>>>>>> 919e9d3b6767d0fceb4a6e035340d2b974bc4ed4
