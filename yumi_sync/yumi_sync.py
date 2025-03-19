import os
import time
import requests
import json
from datetime import datetime
import netifaces
import inotify.adapters  # Nécessite le paquet python-inotify

log_file_path = '/home/pi/YUMI_SYNC/yumi_sync.log'
file_to_monitor = '/home/pi/printer_data/config/printer.cfg'
state_file_path = '/home/pi/monitoring_state.json'
server_url = "http://sync.yumi-lab.com/route_testing"

log_file_path = '/home/pi/YUMI_SYNC//yumi_sync.log'

log_file_path = '/home/pi/YUMI_SYNC//yumi_sync.log'

def get_active_interface():
    try:
        default_gateway = netifaces.gateways()['default']
        default_interface = default_gateway[netifaces.AF_INET][1]
        return default_interface
    except Exception as e:
        print(f"Error getting the active network interface: {e}")
        return None

def get_mac_address(interface_name):
    try:
        iface = netifaces.ifaddresses(interface_name)[netifaces.AF_LINK]
        return iface[0]['addr']
    except KeyError:
        return None

<<<<<<< HEAD
=======
active_interface = get_active_interface()

if active_interface:
    print(f"The active network interface is: {active_interface}")
    mac_address = get_mac_address(active_interface)
    if mac_address:
        print(f"The MAC address of the interface {active_interface} is: {mac_address}")
    else:
        print("Failed to get the MAC address.")
else:
    print("Failed to get the active network interface.")

file_to_monitor = '/home/pi/printer_data/config/printer.cfg'
state_file_path = '/home/pi/monitoring_state.json'
server_url = "http://sync.yumi-lab.com/route_testing"

previous_hash = None

def calculate_file_hash(file_path):
    try:
        with open(file_path, 'rb') as file:
            return hashlib.md5(file.read()).hexdigest()
    except Exception as e:
        print(f"Error calculating file hash: {e}")
        return None

def log_sync_attempt(status, file_name, error_message=None):
    """Log the sync attempt to yumi_sync.log with date-time, file name, and status (OK or ERROR)."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} - {file_name} - {status}"
    if error_message:
        message += f" - {error_message}"
    
    with open(log_file_path, 'a') as log_file:
        log_file.write(message + "\n")

def clean_old_log_entries():
    """Remove log entries older than 3 months."""
    if not os.path.exists(log_file_path):
        return

    cutoff_date = datetime.now() - timedelta(days=90)
    with open(log_file_path, 'r') as log_file:
        lines = log_file.readlines()

    with open(log_file_path, 'w') as log_file:
        for line in lines:
            # Extract the date from the log entry
            try:
                entry_date = datetime.strptime(line.split(" - ")[0], "%Y-%m-%d %H:%M:%S")
                if entry_date >= cutoff_date:
                    log_file.write(line)
            except (IndexError, ValueError):
                # If there's an issue with parsing, skip the line
                continue

<<<<<<< Updated upstream
=======
>>>>>>> 553f62786cd01763c31846fe30a0a50e1c7e908d
>>>>>>> Stashed changes
def send_file_to_server(file_path, timestamp, mac_address):
    try:
        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file)}
<<<<<<< HEAD
            data = {'timestamp': timestamp, 'mac_address': mac_address}
=======
            data = {
                'timestamp': timestamp,
                'mac_address': mac_address
            }
>>>>>>> 553f62786cd01763c31846fe30a0a50e1c7e908d
            response = requests.post(server_url, data=data, files=files)

            if response.status_code == 200:
                log_sync_attempt("OK", file_path)
                print("Data successfully sent to server.")
            else:
                error_message = f"Server responded with status code {response.status_code}"
                log_sync_attempt("ERROR", file_path, error_message)
                print(f"Error sending data to the server: {error_message}")
    except Exception as e:
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
        print(f"Error sending data to the server: {e}")
=======
>>>>>>> Stashed changes
        error_message = str(e)
        log_sync_attempt("ERROR", file_path, error_message)
        print(f"Error sending data to the server: {error_message}")

def load_previous_hash():
    try:
        with open(state_file_path, 'r') as state_file:
            return state_file.read().strip()
    except FileNotFoundError:
        return None

def save_current_hash(current_hash):
    with open(state_file_path, 'w') as state_file:
        state_file.write(current_hash)
>>>>>>> 553f62786cd01763c31846fe30a0a50e1c7e908d

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

<<<<<<< Updated upstream
=======
<<<<<<< HEAD
def monitor_file(file_path):
    i = inotify.adapters.Inotify()
    i.add_watch(file_path)
    
    for event in i.event_gen(yield_nones=False):
        (_, event_type, _, _) = event
        if 'IN_MODIFY' in event_type:  # Si le fichier a été modifié
            print(f"The file {file_path} has been modified. Sending data to the server...")
=======
>>>>>>> Stashed changes
# Clean old log entries before starting
clean_old_log_entries()

while True:
    try:
        current_hash = calculate_file_hash(file_to_monitor)
        if current_hash is not None and current_hash != previous_hash:
            print("The file has changed. Sending data to the server...")
>>>>>>> 553f62786cd01763c31846fe30a0a50e1c7e908d
            timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
            mac_address = get_mac_address(get_active_interface())
            if mac_address:
                send_file_to_server(file_path, timestamp, mac_address)
            else:
                print("Failed to get the MAC address.")

            last_sent_date = load_last_sent_date()
            if last_sent_date is None or (datetime.now() - datetime.strptime(last_sent_date, "%Y-%m-%d")).days >= 30:
                print("Sending the file as it has been 30 days or more...")
                send_file_to_server(file_path, timestamp, mac_address)
                save_last_sent_date(time.strftime("%Y-%m-%d"))

<<<<<<< Updated upstream
        # Change the sleep time to one hour (3600 seconds)
        time.sleep(3600)
=======
<<<<<<< HEAD
if __name__ == "__main__":
    try:
        monitor_file(file_to_monitor)
=======
        # Change the sleep time to one hour (3600 seconds)
        time.sleep(3600)
>>>>>>> 553f62786cd01763c31846fe30a0a50e1c7e908d
>>>>>>> Stashed changes
    except KeyboardInterrupt:
        print("Monitoring stopped.")
    except Exception as e:
        print(f"Error in monitoring: {e}")
