import os
import time
import requests
import hashlib
import json
import logging
from datetime import datetime, timedelta
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
POLL_INTERVAL = 30  # seconds
CLIENT_BOOT_DELAY_DAYS = 15  # days after factory QC to detect client first boot

def get_mac_address(interface_name):
    try:
        iface = netifaces.ifaddresses(interface_name)[netifaces.AF_LINK]
        return iface[0]['addr']
    except KeyError:
        logging.error("MAC address not found for interface: %s", interface_name)
        return None

mac_address = get_mac_address(FORCED_INTERFACE)
if not mac_address:
    logging.error("MAC address not found. Exiting script.")
    exit(1)

logging.info("MAC address detected: %s", mac_address)

def calculate_file_hash(file_path):
    try:
        with open(file_path, 'rb') as file:
            return hashlib.md5(file.read()).hexdigest()
    except Exception as e:
        logging.error("Error calculating file hash: %s", e)
        return None

def send_file_to_server(file_path, mac_address):
    hexid = mac_address.replace(":", "").upper()
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    logging.info("Sending printer.cfg to server... HEX = %s", hexid)

    with open(file_path, 'rb') as file:
        files = {'file': (os.path.basename(file_path), file)}
        data = {'timestamp': timestamp, 'hexid': hexid}
        headers = {'User-Agent': 'YumiSyncClient/2.0'}
        response = requests.post(server_url, data=data, files=files, headers=headers, timeout=15)
        response.raise_for_status()
        logging.info("File successfully sent to server.")

def load_state():
    try:
        with open(state_file_path, 'r') as f:
            content = f.read().strip()
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # V1 legacy: state file was plain text hash (32 hex chars)
                if content and len(content) == 32:
                    logging.info("Migrating v1 state file to v2 format...")
                    migrated = {
                        'last_hash': content,
                        'first_boot_date': datetime.now().isoformat(),
                        'client_registered': True
                    }
                    save_state(migrated)
                    return migrated
                return {}
    except FileNotFoundError:
        return {}

def save_state(state):
    try:
        with open(state_file_path, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        logging.error("Failed to write state file: %s", e)

def main():
    state = load_state()
    previous_hash = state.get('last_hash')

    # First boot (factory QC): no state file yet
    if not previous_hash:
        current_hash = calculate_file_hash(file_to_monitor)
        if current_hash:
            logging.info("First boot detected (factory QC), registering device...")
            try:
                send_file_to_server(file_to_monitor, mac_address)
                state = {
                    'last_hash': current_hash,
                    'first_boot_date': datetime.now().isoformat(),
                    'client_registered': False
                }
                save_state(state)
                previous_hash = current_hash
                logging.info("Device registered (factory QC).")
            except Exception as e:
                logging.error("First boot send failed: %s", e)

    # Client first boot: >15 days after factory QC, not yet registered
    if not state.get('client_registered') and state.get('first_boot_date'):
        try:
            first_boot = datetime.fromisoformat(state['first_boot_date'])
            if datetime.now() - first_boot > timedelta(days=CLIENT_BOOT_DELAY_DAYS):
                current_hash = calculate_file_hash(file_to_monitor)
                if current_hash:
                    logging.info("Client first boot detected (>%d days since QC), sending config...", CLIENT_BOOT_DELAY_DAYS)
                    try:
                        send_file_to_server(file_to_monitor, mac_address)
                        state['last_hash'] = current_hash
                        state['client_registered'] = True
                        state['client_boot_date'] = datetime.now().isoformat()
                        save_state(state)
                        previous_hash = current_hash
                        logging.info("Client registered.")
                    except Exception as e:
                        logging.error("Client boot send failed: %s", e)
        except (ValueError, TypeError) as e:
            logging.error("Invalid first_boot_date in state: %s", e)

    logging.info("Yumi Sync client started (poll every %ds)", POLL_INTERVAL)

    # Main loop: only send on file change
    while True:
        try:
            current_hash = calculate_file_hash(file_to_monitor)

            if current_hash and current_hash != previous_hash:
                try:
                    send_file_to_server(file_to_monitor, mac_address)
                    state['last_hash'] = current_hash
                    save_state(state)
                    previous_hash = current_hash
                except Exception as e:
                    logging.error("Send failed: %s", e)

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logging.info("Script manually stopped.")
            break
        except Exception as e:
            logging.error("Unexpected error in main loop: %s", e)
            time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    main()
