#!/bin/bash

RUTA_SCRIPT="/opt/YUMI_SYNC/yumi_sync.py"
RUTA_SERVICIO="/etc/systemd/system/yumi_sync.service"

if [ ! -d "/opt/YUMI_SYNC" ]; then
    mkdir -p /opt/YUMI_SYNC
fi

cat << 'EOF' > "$RUTA_SCRIPT"
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


cat > "$RUTA_SERVICIO" <<EOL
[Unit]
Description=Yumi Sync Service

[Service]
ExecStart=/usr/bin/python3 $RUTA_SCRIPT
WorkingDirectory=/opt/YUMI_SYNC
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOL

systemctl daemon-reload

systemctl start yumi_sync

systemctl enable yumi_sync

echo "Instalation completed. Server running."
