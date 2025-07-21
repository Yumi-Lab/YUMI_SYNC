import os
import time
import requests
import hashlib
import json
import logging
from datetime import datetime
import netifaces

# === LOG CONFIGURATION ===
logging.basicConfig(
    filename='/home/pi/printer_data/logs/yumi_sync.log',
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)

file_to_monitor = '/home/pi/printer_data/config/printer.cfg'
state_file_path = '/home/pi/monitoring_state.json'
server_url = "http://yumi-id.yumi-lab.com/upload"
FORCED_INTERFACE = 'end0'

def get_mac_address(interface_name):
    try:
        iface = netifaces.ifaddresses(interface_name)[netifaces.AF_LINK]
        return iface[0]['addr']
    except KeyError:
        logging.error("❌ MAC address not found for interface: %s", interface_name)
        return None

mac_address = get_mac_address(FORCED_INTERFACE)
if not mac_address:
    logging.error("❌ MAC address not found. Exiting script.")
    exit(1)

logging.info("✅ MAC address detected: %s", mac_address)

def calculate_file_hash(file_path):
    try:
        with open(file_path, 'rb') as file:
            return hashlib.md5(file.read()).hexdigest()
    except Exception as e:
        logging.error("❌ Error calculating file hash: %s", e)
        return None

def send_file_to_server(file_path, timestamp, mac_address):
    try:
        hexid = mac_address.replace(":", "").upper()
        logging.info("📤 printer.cfg change detected. Sending to server... HEX = %s", hexid)

        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file)}
            data = {'timestamp': timestamp, 'hexid': hexid}
            headers = {'User-Agent': 'YumiSyncClient/1.0'}
            response = requests.post(server_url, data=data, files=files, headers=headers, timeout=10)

            if response.status_code == 200:
                logging.info("✅ File successfully sent to server.")
            else:
                logging.error("❌ Server error %s during upload.", response.status_code)
    except Exception as e:
        logging.error("❌ Exception during file upload: %s", e)

def load_state():
    try:
        with open(state_file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_state(state):
    try:
        with open(state_file_path, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        logging.error("❌ Failed to write state file: %s", e)

state = load_state()
previous_hash = state.get('last_hash')
previous_mtime = state.get('last_mtime')
last_sent_date = state.get('last_sent_date')

logging.info("🚀 Yumi Sync client started")

while True:
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        try:
            current_mtime = os.path.getmtime(file_to_monitor)
        except FileNotFoundError:
            logging.warning("⚠️ File not found: %s", file_to_monitor)
            time.sleep(5)
            continue

        current_hash = calculate_file_hash(file_to_monitor)

        if (
            current_hash
            and current_hash != previous_hash
            and current_mtime != previous_mtime
        ):
            send_file_to_server(file_to_monitor, timestamp, mac_address)
            state['last_hash'] = current_hash
            state['last_mtime'] = current_mtime
            state['last_sent_date'] = today_str
            save_state(state)
            previous_hash = current_hash
            previous_mtime = current_mtime

        elif last_sent_date is None or (datetime.now() - datetime.strptime(last_sent_date, "%Y-%m-%d")).days >= 30:
            logging.info("📅 30 days elapsed. Scheduled file send.")
            send_file_to_server(file_to_monitor, timestamp, mac_address)
            state['last_hash'] = current_hash
            state['last_mtime'] = current_mtime
            state['last_sent_date'] = today_str
            save_state(state)
            previous_hash = current_hash
            previous_mtime = current_mtime

        time.sleep(5)

    except KeyboardInterrupt:
        logging.info("🛑 Script manually stopped.")
        break
    except Exception as e:
        logging.error("❌ Unexpected error in main loop: %s", e)
