import os
import subprocess
import time
import threading
import requests
import hashlib
import json
import logging
from datetime import datetime, timedelta
import netifaces
try:
    import websocket
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False
    logging.warning("websocket-client not installed — MCU watchdog will use HTTP polling only")

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

# === MCU WATCHDOG CONFIG ===
MOONRAKER_URL = "http://localhost:7125"
MCU_WATCHDOG_MAX_RETRIES = 3
MCU_WATCHDOG_RETRY_COOLDOWN = 30  # seconds between retry attempts
MCU_WATCHDOG_BACKOFF_COOLDOWN = 300  # seconds after max retries exhausted
MCU_ERROR_LOG = '/home/pi/printer_data/config/yumi_sync_log.cfg'
MCU_ERROR_LOG_MAX_ENTRIES = 50

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

# === SELF-REPAIR: Fix systemd service file ===
# Ensure ExecStartPre is present to auto-recreate venv if missing

def fix_own_service_file():
    service_file = '/etc/systemd/system/yumi_sync.service'
    ensure_script = '/home/pi/YUMI_SYNC/scripts/ensure_venv.sh'
    exec_start_pre = 'ExecStartPre=/bin/bash %s' % ensure_script

    if not os.path.isfile(ensure_script):
        return

    try:
        with open(service_file, 'r') as f:
            content = f.read()

        if 'ExecStartPre' in content:
            return  # Already patched

        # Insert ExecStartPre before ExecStart
        new_content = content.replace(
            'ExecStart=',
            '%s\nExecStart=' % exec_start_pre,
            1
        )

        with open(service_file, 'w') as f:
            f.write(new_content)

        subprocess.run(['systemctl', 'daemon-reload'], check=True)
        logging.info("Service file updated with ExecStartPre for venv auto-repair")

    except Exception as e:
        logging.error("Failed to fix service file: %s", e)

# === SELF-REPAIR: Fix Moonraker update config ===
# Old installs have managed_services: YUMI_SYNC (uppercase) but systemd service is yumi_sync (lowercase)

def fix_own_moonraker_config():
    config_paths = [
        '/home/pi/printer_data/config/update_YUMI_SYNC.cfg',
        '/home/pi/printer_data/config/update_yumi_sync.cfg',
    ]
    correct_config = """[update_manager yumi_sync]
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
        if ('managed_services: YUMI_SYNC' in content
                or 'install_script' in content
                or 'requirements:' in content
                or 'system_dependencies' not in content):
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


# === PLYMOUTH THEME FIX (Bookworm only) ===
# armbian-plymouth-theme postinst overwrites plymouthd.conf with Theme=armbian on every upgrade.
# Restore our theme: prefer yumi-klipper, fallback to hexagon_alt.

PLYMOUTH_CONF = '/etc/plymouth/plymouthd.conf'
PLYMOUTH_THEMES_DIR = '/usr/share/plymouth/themes'
PLYMOUTH_PREFERRED = ['yumi-klipper', 'hexagon_alt']

def fix_plymouth_theme():
    # Only run on Bookworm (Debian 12)
    try:
        with open('/etc/os-release', 'r') as f:
            os_info = f.read()
        if 'bookworm' not in os_info:
            return
    except Exception:
        return

    # Find the best available theme
    target_theme = None
    for theme in PLYMOUTH_PREFERRED:
        theme_path = os.path.join(PLYMOUTH_THEMES_DIR, theme, f'{theme}.plymouth')
        if os.path.isfile(theme_path):
            target_theme = theme
            break

    if not target_theme:
        return

    # Check if already correct
    try:
        with open(PLYMOUTH_CONF, 'r') as f:
            current = f.read()
        if f'Theme={target_theme}' in current:
            return
    except FileNotFoundError:
        return

    # Theme was overwritten (likely by armbian-plymouth-theme upgrade)
    logging.info("Plymouth theme was changed, restoring %s...", target_theme)

    result = subprocess.run(
        ['plymouth-set-default-theme', target_theme],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        logging.error("plymouth-set-default-theme failed: %s", result.stderr)
        return

    # Rebuild initramfs so boot splash matches
    logging.info("Rebuilding initramfs with theme %s...", target_theme)
    result = subprocess.run(
        ['update-initramfs', '-u'],
        capture_output=True, text=True, timeout=300
    )
    if result.returncode == 0:
        logging.info("Plymouth theme fix applied — %s in rootfs + initramfs", target_theme)
    else:
        logging.error("update-initramfs failed: %s", result.stderr)


# === KLIPPER MCU (LINUX) PRIORITY FIX ===
# klipper_mcu runs as a Linux process using a software timer (no hardware crystal).
# Without elevated priority, the timer drifts (~49.998 MHz vs 50 MHz target) and
# Klipper reports clock frequency errors.  Setting Nice=-20 gives the process
# highest non-RT priority, which keeps the timer accurate.

KLIPPER_MCU_SERVICE = '/etc/systemd/system/klipper-mcu.service'

def fix_klipper_mcu_priority():
    if not os.path.isfile(KLIPPER_MCU_SERVICE):
        return  # No linux MCU on this machine

    try:
        with open(KLIPPER_MCU_SERVICE, 'r') as f:
            content = f.read()
    except Exception as e:
        logging.error("Cannot read %s: %s", KLIPPER_MCU_SERVICE, e)
        return

    if 'Nice=-20' in content:
        return  # Already patched

    # Insert Nice=-20 in [Service] section, before ExecStart
    if 'ExecStart=' not in content:
        logging.error("klipper-mcu.service has no ExecStart line, skipping fix")
        return

    new_content = content.replace(
        'ExecStart=',
        'Nice=-20\nExecStart=',
        1
    )

    try:
        with open(KLIPPER_MCU_SERVICE, 'w') as f:
            f.write(new_content)
        subprocess.run(['systemctl', 'daemon-reload'], check=True)
        # Do NOT restart klipper-mcu here — it would kill the MCU socket
        # while Klipper is running and cause a cascade of errors.
        # The fix takes effect on next Pi reboot.
        logging.info("klipper-mcu.service patched with Nice=-20 (active on next reboot)")
    except Exception as e:
        logging.error("Failed to fix klipper-mcu priority: %s", e)


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
                'MOONRAKER_PROCESS_UID': '1',  # Signal to install.sh: this is an update, not first install
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

# === MCU WATCHDOG (WebSocket) ===
# Subscribes to Moonraker WebSocket notifications for instant MCU error detection.
# On notify_klippy_shutdown / notify_klippy_disconnected, queries printer state
# and sends FIRMWARE_RESTART immediately — no 30s polling delay.
# Falls back to HTTP polling if WebSocket is unavailable.

MOONRAKER_WS_URL = "ws://localhost:7125/websocket"

MCU_ERROR_PATTERNS = [
    "lost communication with mcu",
    "timer too close",
    "mcu shutdown",
    "mcu_connect",
    "can not update mcu",
    "unable to connect",
    "unable to open serial port",
    "serial connection closed",
    "timeout with mcu",
    "communication timeout",
    "mcu protocol error",
]

class McuWatchdog:
    def __init__(self):
        self.retry_count = 0
        self.last_restart_time = 0
        self._ws = None
        self._ws_connected = False
        self._ws_thread = None

    # --- HTTP helpers (used by both WS callback and fallback polling) ---

    def _get_printer_info(self):
        try:
            resp = requests.get(f"{MOONRAKER_URL}/printer/info", timeout=5)
            resp.raise_for_status()
            return resp.json().get('result', {})
        except Exception:
            return None

    def _get_print_status(self):
        try:
            resp = requests.get(f"{MOONRAKER_URL}/printer/objects/query?print_stats", timeout=5)
            resp.raise_for_status()
            data = resp.json().get('result', {}).get('status', {}).get('print_stats', {})
            return data.get('state', '')
        except Exception:
            return ''

    def _is_mcu_error(self, message):
        msg_lower = message.lower()
        for pattern in MCU_ERROR_PATTERNS:
            if pattern in msg_lower:
                return True
        return False

    def _send_firmware_restart(self):
        try:
            resp = requests.post(f"{MOONRAKER_URL}/printer/firmware_restart", timeout=10)
            resp.raise_for_status()
            logging.info("[MCU-WATCHDOG] FIRMWARE_RESTART sent successfully")
            return True
        except Exception as e:
            logging.warning("[MCU-WATCHDOG] FIRMWARE_RESTART failed: %s", e)
            return False

    def _send_klipper_restart(self):
        try:
            resp = requests.post(f"{MOONRAKER_URL}/printer/restart", timeout=10)
            resp.raise_for_status()
            logging.info("[MCU-WATCHDOG] Full Klipper restart sent")
            return True
        except Exception as e:
            logging.warning("[MCU-WATCHDOG] Full Klipper restart failed: %s", e)
            return False

    # --- Persistent error log (visible in Mainsail file browser) ---

    def _log_mcu_error(self, state, message):
        """Append error to mcu_error.log in config dir, keep last N entries."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        entry = f"[{timestamp}] state={state} | {message}"

        try:
            # Read existing entries
            lines = []
            if os.path.isfile(MCU_ERROR_LOG):
                with open(MCU_ERROR_LOG, 'r') as f:
                    lines = [l.rstrip('\n') for l in f.readlines() if l.strip()]

            # Append new entry, trim to max
            lines.append(entry)
            lines = lines[-MCU_ERROR_LOG_MAX_ENTRIES:]

            with open(MCU_ERROR_LOG, 'w') as f:
                f.write('\n'.join(lines) + '\n')

        except Exception as e:
            logging.error("[MCU-WATCHDOG] Failed to write %s: %s", MCU_ERROR_LOG, e)

    # --- Core logic: attempt recovery ---

    def _attempt_recovery(self, state, message):
        """Attempt MCU recovery with retry/backoff logic. Thread-safe via GIL."""
        # Log every MCU error to persistent file (before any skip/cooldown)
        self._log_mcu_error(state, message)

        # Skip if actively printing — but only if Klipper is still functional.
        # When Klipper is in shutdown, the print is dead anyway and print_stats
        # may still report 'paused'/'printing' as stale state.
        print_status = self._get_print_status()
        if print_status in ('printing', 'paused') and state not in ('shutdown',):
            logging.warning("[MCU-WATCHDOG] MCU error but print is %s — skipping", print_status)
            return

        now = time.time()

        # Backoff: exhausted max retries
        if self.retry_count >= MCU_WATCHDOG_MAX_RETRIES:
            if (now - self.last_restart_time) < MCU_WATCHDOG_BACKOFF_COOLDOWN:
                return
            logging.warning("[MCU-WATCHDOG] Backoff expired, resetting retry counter")
            self.retry_count = 0

        # Cooldown between attempts
        if self.retry_count > 0 and (now - self.last_restart_time) < MCU_WATCHDOG_RETRY_COOLDOWN:
            return

        self.retry_count += 1
        self.last_restart_time = now
        logging.warning("[MCU-WATCHDOG] MCU error (attempt %d/%d): state=%s msg=%s",
                        self.retry_count, MCU_WATCHDOG_MAX_RETRIES, state, message[:200])

        if self.retry_count <= 2:
            self._send_firmware_restart()
        else:
            logging.warning("[MCU-WATCHDOG] FIRMWARE_RESTART failed %d times, full restart",
                            self.retry_count - 1)
            self._send_klipper_restart()

    # --- WebSocket callbacks ---

    def _on_ws_message(self, ws, raw):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return

        method = data.get('method', '')

        # Moonraker pushes these when Klipper loses connection or shuts down
        if method in ('notify_klippy_shutdown', 'notify_klippy_disconnected'):
            logging.info("[MCU-WATCHDOG] WS event: %s", method)
            # Wait for Klipper to settle — after SAVE_CONFIG it goes through
            # shutdown → disconnected → startup → error, takes ~5-10s
            time.sleep(8)
            info = self._get_printer_info()
            if not info:
                # Moonraker still up but Klipper not responding yet, retry once
                time.sleep(5)
                info = self._get_printer_info()
            if not info:
                logging.warning("[MCU-WATCHDOG] Cannot reach Moonraker after %s", method)
                return
            state = info.get('state', '')
            message = info.get('state_message', '')
            logging.info("[MCU-WATCHDOG] Post-event state=%s msg=%s", state, message[:200])
            # If Klipper is still stuck after 8s, attempt recovery regardless
            # of the error message — any shutdown/error that doesn't self-resolve
            # needs a FIRMWARE_RESTART
            if state in ('error', 'shutdown'):
                self._attempt_recovery(state, message)

        # Klipper is back online — reset retry counter
        elif method == 'notify_klippy_ready':
            if self.retry_count > 0:
                logging.info("[MCU-WATCHDOG] Klipper recovered after %d attempt(s)", self.retry_count)
                self.retry_count = 0

    def _on_ws_open(self, ws):
        self._ws_connected = True
        logging.info("[MCU-WATCHDOG] WebSocket connected to Moonraker")

    def _on_ws_close(self, ws, close_status_code, close_msg):
        self._ws_connected = False
        logging.warning("[MCU-WATCHDOG] WebSocket disconnected (code=%s)", close_status_code)

    def _on_ws_error(self, ws, error):
        self._ws_connected = False
        logging.warning("[MCU-WATCHDOG] WebSocket error: %s", error)

    # --- Start WebSocket listener in daemon thread ---

    def start(self):
        """Start the WebSocket listener thread. Call once from main()."""
        if not HAS_WEBSOCKET:
            logging.info("[MCU-WATCHDOG] No websocket-client, running in HTTP polling mode only")
            return

        def _ws_loop():
            while True:
                try:
                    self._ws = websocket.WebSocketApp(
                        MOONRAKER_WS_URL,
                        on_message=self._on_ws_message,
                        on_open=self._on_ws_open,
                        on_close=self._on_ws_close,
                        on_error=self._on_ws_error,
                    )
                    self._ws.run_forever(ping_interval=30, ping_timeout=10)
                except Exception as e:
                    logging.error("[MCU-WATCHDOG] WS loop error: %s", e)
                # Reconnect after 5s if disconnected
                self._ws_connected = False
                time.sleep(5)

        self._ws_thread = threading.Thread(target=_ws_loop, name="mcu-watchdog-ws", daemon=True)
        self._ws_thread.start()
        logging.info("[MCU-WATCHDOG] WebSocket listener started (thread=%s)", self._ws_thread.name)

    # --- Fallback: poll check (called from main loop if WS is down) ---

    def check(self):
        """Fallback polling check — only runs if WebSocket is not connected."""
        if self._ws_connected:
            return  # WS is handling it in real-time

        info = self._get_printer_info()
        if not info:
            return

        state = info.get('state', '')
        message = info.get('state_message', '')

        if state == 'ready':
            if self.retry_count > 0:
                logging.info("[MCU-WATCHDOG] Klipper recovered after %d attempt(s)", self.retry_count)
                self.retry_count = 0
            return

        if state == 'startup':
            return

        if state in ('error', 'shutdown'):
            self._attempt_recovery(state, message)


def main():
    # Fix own service file (add ExecStartPre for venv auto-repair)
    try:
        fix_own_service_file()
    except Exception as e:
        logging.error("Service file fix failed: %s", e)

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

    # Fix Plymouth theme if overwritten by armbian-plymouth-theme upgrade
    try:
        fix_plymouth_theme()
    except Exception as e:
        logging.error("Plymouth theme fix failed: %s", e)

    # Fix klipper-mcu linux process priority (Nice=-20 for accurate 50MHz timer)
    try:
        fix_klipper_mcu_priority()
    except Exception as e:
        logging.error("klipper-mcu priority fix failed: %s", e)

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

    # Initialize MCU watchdog (WebSocket + HTTP fallback)
    mcu_watchdog = McuWatchdog()
    mcu_watchdog.start()
    logging.info("[MCU-WATCHDOG] Active (ws=%s, max_retries=%d, cooldown=%ds, backoff=%ds)",
                 MOONRAKER_WS_URL, MCU_WATCHDOG_MAX_RETRIES,
                 MCU_WATCHDOG_RETRY_COOLDOWN, MCU_WATCHDOG_BACKOFF_COOLDOWN)

    # Main loop: config sync + MCU watchdog
    while True:
        try:
            # --- Config file sync ---
            current_hash = calculate_file_hash(file_to_monitor)

            if current_hash and current_hash != previous_hash:
                try:
                    send_file_to_server(file_to_monitor, mac_address)
                    state['last_hash'] = current_hash
                    save_state(state)
                    previous_hash = current_hash
                except Exception as e:
                    logging.error("Send failed: %s", e)

            # --- MCU watchdog ---
            try:
                mcu_watchdog.check()
            except Exception as e:
                logging.error("[MCU-WATCHDOG] Check failed: %s", e)

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logging.info("Script manually stopped.")
            break
        except Exception as e:
            logging.error("Unexpected error in main loop: %s", e)
            time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    main()
