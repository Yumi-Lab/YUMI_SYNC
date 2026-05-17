import os
import subprocess
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

# === SELF-REPAIR: Fix Moonraker update config ===
# Old installs have managed_services: YUMI_SYNC (uppercase) but systemd service is yumi_sync (lowercase)

def fix_own_moonraker_config():
    config_paths = [
        '/home/pi/printer_data/config/update_YUMI_SYNC.cfg',
        '/home/pi/printer_data/config/update_yumi_sync.cfg',
    ]
    correct_config = """# YUMI_SYNC update_manager entry
[update_manager yumi_sync]
type: git_repo
path: ~/YUMI_SYNC
origin: https://github.com/Yumi-Lab/YUMI_SYNC.git
primary_branch: main
managed_services: yumi_sync
system_dependencies: system_dependencies.json
"""
    # Check if old uppercase config exists
    old_cfg = '/home/pi/printer_data/config/update_YUMI_SYNC.cfg'
    new_cfg = '/home/pi/printer_data/config/update_yumi_sync.cfg'

    needs_fix = False
    if os.path.isfile(old_cfg):
        needs_fix = True
        os.remove(old_cfg)
        logging.info("Removed old update_YUMI_SYNC.cfg")
    if os.path.isfile(new_cfg):
        with open(new_cfg, 'r') as f:
            content = f.read()
        if 'managed_services: YUMI_SYNC' in content or 'system_dependencies' not in content:
            needs_fix = True
    else:
        needs_fix = True

    if needs_fix:
        with open(new_cfg, 'w') as f:
            f.write(correct_config)
        logging.info("Fixed YUMI_SYNC moonraker update config (lowercase service name)")

        # Fix moonraker.conf include
        moonraker_conf = '/home/pi/printer_data/config/moonraker.conf'
        if os.path.isfile(moonraker_conf):
            with open(moonraker_conf, 'r') as f:
                conf = f.read()
            changed = False
            if '[include update_YUMI_SYNC.cfg]' in conf:
                conf = conf.replace('[include update_YUMI_SYNC.cfg]', '[include update_yumi_sync.cfg]')
                changed = True
            if '[include update_yumi_sync.cfg]' not in conf:
                conf = '[include update_yumi_sync.cfg]\n' + conf
                changed = True
            if changed:
                with open(moonraker_conf, 'w') as f:
                    f.write(conf)
                logging.info("Fixed moonraker.conf include for yumi_sync")

    # Ensure yumi_sync is in moonraker.asvc (allowed services)
    asvc_path = '/home/pi/printer_data/moonraker.asvc'
    if os.path.isfile(asvc_path):
        with open(asvc_path, 'r') as f:
            asvc_content = f.read()
        if 'yumi_sync' not in asvc_content:
            with open(asvc_path, 'a') as f:
                f.write('\nyumi_sync\n')
            logging.info("Added yumi_sync to moonraker.asvc")

# === CPU GOVERNOR FIX (Bookworm only) ===
# V1 pads on Debian 12 had a broken set-cpu-freq.service that disabled itself after first boot.
# Fix: write correct /etc/default/cpufrequtils once, let cpufrequtils handle it natively.
# Debian 13 (trixie) images already have this right from the build.

CPUFREQ_CONFIG = '/etc/default/cpufrequtils'
CPUFREQ_CORRECT = """ENABLE=true
GOVERNOR=userspace
MIN_SPEED=960000
MAX_SPEED=960000
"""

def fix_cpu_governor():
    # Only run on Bookworm (Debian 12)
    try:
        with open('/etc/os-release', 'r') as f:
            os_info = f.read()
        if 'bookworm' not in os_info:
            return
    except Exception:
        return

    # Check if already correct
    try:
        with open(CPUFREQ_CONFIG, 'r') as f:
            current = f.read()
        if 'GOVERNOR=userspace' in current and 'MIN_SPEED=960000' in current and 'MAX_SPEED=960000' in current and 'ENABLE=true' in current:
            return
    except FileNotFoundError:
        pass

    # Write correct config
    logging.info("Fixing CPU governor config for Bookworm (userspace 960MHz)...")
    try:
        with open(CPUFREQ_CONFIG, 'w') as f:
            f.write(CPUFREQ_CORRECT)
        logging.info("Wrote %s", CPUFREQ_CONFIG)
    except PermissionError:
        logging.error("Cannot write %s — not running as root?", CPUFREQ_CONFIG)
        return

    # Remove old broken set-cpu-freq service + script
    old_service = '/etc/systemd/system/set-cpu-freq.service'
    old_script = '/usr/local/bin/set_cpu_freq.sh'
    if os.path.isfile(old_service):
        subprocess.run(['systemctl', 'disable', 'set-cpu-freq.service'], capture_output=True)
        subprocess.run(['systemctl', 'stop', 'set-cpu-freq.service'], capture_output=True)
        os.remove(old_service)
        subprocess.run(['systemctl', 'daemon-reload'], capture_output=True)
        logging.info("Removed old set-cpu-freq.service")
    if os.path.isfile(old_script):
        os.remove(old_script)
        logging.info("Removed old %s", old_script)

    # Restart cpufrequtils to apply immediately
    subprocess.run(['systemctl', 'restart', 'cpufrequtils'], capture_output=True)
    logging.info("CPU governor fix applied — userspace 960MHz")



# === REPO INSTALL REPAIR ===
# Tracks install.sh hash per repo. If changed (or first run), re-executes it.
# Moonraker only does git pull — it never runs install scripts.

INSTALL_STATE_PATH = '/home/pi/.yumi_install_state.json'
MANAGED_REPOS = [
    {'name': 'yumi-config', 'path': '/home/pi/yumi-config', 'script': 'install.sh'},
    {'name': 'YUMI_PLR', 'path': '/home/pi/YUMI_PLR', 'script': 'install.sh'},
    {'name': 'moonraker-yumi-lab', 'path': '/home/pi/moonraker-yumi-lab', 'script': 'install.sh', 'args': ['-U', '-L']},       # V1
    {'name': 'moonraker-app-yumi-lab', 'path': '/home/pi/moonraker-app-yumi-lab', 'script': 'install.sh', 'args': ['-U', '-L']},  # V2
]

def _load_install_state():
    try:
        with open(INSTALL_STATE_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_install_state(state):
    try:
        with open(INSTALL_STATE_PATH, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        logging.error("Failed to write install state: %s", e)

def repair_repos():
    install_state = _load_install_state()
    for repo in MANAGED_REPOS:
        script_path = os.path.join(repo['path'], repo['script'])
        if not os.path.isfile(script_path):
            continue
        current_hash = calculate_file_hash(script_path)
        if not current_hash:
            continue
        saved_hash = install_state.get(repo['name'])
        if current_hash == saved_hash:
            continue
        logging.info("Repo %s: install.sh changed (hash %s -> %s), executing...",
                     repo['name'], saved_hash or 'NONE', current_hash)
        try:
            cmd = ['bash', repo['script']] + repo.get('args', [])
            env = os.environ.copy()
            env.update({
                'HOME': '/home/pi',
                'USER': 'pi',
                'LOGNAME': 'pi',
                'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
            })
            result = subprocess.run(
                cmd,
                cwd=repo['path'],
                env=env,
                capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0:
                logging.info("Repo %s: install.sh executed successfully", repo['name'])
                if result.stdout:
                    logging.debug("Repo %s stdout: %s", repo['name'], result.stdout[-1000:])
                install_state[repo['name']] = current_hash
                _save_install_state(install_state)
            else:
                logging.error("Repo %s: install.sh failed (exit %d)\nstderr: %s\nstdout: %s",
                              repo['name'], result.returncode,
                              result.stderr[-500:] if result.stderr else '',
                              result.stdout[-500:] if result.stdout else '')
        except subprocess.TimeoutExpired:
            logging.error("Repo %s: install.sh timed out (300s)", repo['name'])
        except Exception as e:
            logging.error("Repo %s: install.sh error: %s", repo['name'], e)

def main():
    # Fix own moonraker config (uppercase -> lowercase service name)
    try:
        fix_own_moonraker_config()
    except Exception as e:
        logging.error("Self-repair config failed: %s", e)

    # Fix CPU governor on Bookworm (one-shot)
    try:
        fix_cpu_governor()
    except Exception as e:
        logging.error("CPU governor fix failed: %s", e)

    # Run install repair before main sync loop
    try:
        repair_repos()
    except Exception as e:
        logging.error("Repo repair failed: %s", e)

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
