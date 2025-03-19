#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import hashlib
import json
import requests
import netifaces
from datetime import datetime, timedelta
from inotify.adapters import Inotify

# Configuration
CONFIG = {
    'FILE_TO_MONITOR': os.getenv('MONITOR_FILE', '/home/pi/printer_data/config/printer.cfg'),
    'STATE_FILE': os.getenv('STATE_FILE', '/home/pi/monitoring_state.json'),
    'SERVER_URL': os.getenv('SYNC_SERVER', 'https://sync.yumi-lab.com/route_testing'),
    'LOG_FILE': os.getenv('LOG_FILE', '/home/pi/YUMI_SYNC/yumi_sync.log'),
    'CHECK_INTERVAL': 3600,  # 1 hour fallback check
    'LOG_RETENTION_DAYS': 90
}

def setup_logging():
    os.makedirs(os.path.dirname(CONFIG['LOG_FILE']), exist_ok=True)

def get_network_info():
    """Get active network interface and MAC address with fallback"""
    try:
        gateway_info = netifaces.gateways().get('default', {})
        interface = gateway_info.get(netifaces.AF_INET, (None, None, None))[1]
        
        if interface:
            mac = netifaces.ifaddresses(interface)[netifaces.AF_LINK][0]['addr']
            return interface, mac
        
    except Exception as e:
        log_error(f"Network detection error: {str(e)}")

    # Fallback to first available interface
    for iface in ['eth0', 'wlan0']:
        try:
            mac = netifaces.ifaddresses(iface)[netifaces.AF_LINK][0]['addr']
            return iface, mac
        except:
            continue
    
    return None, None

def log_sync(status, message, file_name=None):
    """Log synchronization attempts"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} - {status} - {message}"
    
    if file_name:
        log_entry += f" - File: {file_name}"
    
    with open(CONFIG['LOG_FILE'], 'a') as f:
        f.write(log_entry + "\n")

def log_error(message):
    log_sync("ERROR", message)

def clean_old_logs():
    """Remove log entries older than retention period"""
    if not os.path.exists(CONFIG['LOG_FILE']):
        return

    cutoff = datetime.now() - timedelta(days=CONFIG['LOG_RETENTION_DAYS'])
    new_logs = []

    with open(CONFIG['LOG_FILE'], 'r') as f:
        for line in f:
            try:
                log_date = datetime.strptime(line.split(" - ")[0], "%Y-%m-%d %H:%M:%S")
                if log_date > cutoff:
                    new_logs.append(line)
            except:
                continue

    with open(CONFIG['LOG_FILE'], 'w') as f:
        f.writelines(new_logs)

def send_to_server(file_path, mac_address):
    """Send file to server with security features"""
    try:
        file_name = os.path.basename(file_path)
        timestamp = datetime.now().isoformat()
        
        with open(file_path, 'rb') as f:
            files = {'file': (file_name, f)}
            data = {
                'timestamp': timestamp,
                'mac_address': mac_address,
                'file_hash': calculate_sha256(file_path)
            }
            
            response = requests.post(
                CONFIG['SERVER_URL'],
                files=files,
                data=data,
                timeout=10,
                verify=True  # Enable SSL verification
            )
            
            if response.status_code == 200:
                log_sync("SUCCESS", "File transferred", file_name)
                return True
            else:
                log_error(f"Server error: {response.status_code}")
                return False
                
    except Exception as e:
        log_error(f"Transfer failed: {str(e)}")
        return False

def calculate_sha256(file_path):
    """Calculate SHA-256 file hash"""
    sha = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(4096):
            sha.update(chunk)
    return sha.hexdigest()

def update_state():
    """Update last sync timestamp in state file"""
    state = {
        'last_sync': datetime.now().isoformat(),
        'last_hash': calculate_sha256(CONFIG['FILE_TO_MONITOR'])
    }
    
    with open(CONFIG['STATE_FILE'], 'w') as f:
        json.dump(state, f)

def should_send_interval():
    """Check if we should send based on 30-day interval"""
    try:
        with open(CONFIG['STATE_FILE'], 'r') as f:
            state = json.load(f)
            last_sync = datetime.fromisoformat(state['last_sync'])
            return (datetime.now() - last_sync).days >= 30
    except:
        return True

def main():
    setup_logging()
    clean_old_logs()
    
    interface, mac_address = get_network_info()
    if not mac_address:
        log_error("No valid network interface found")
        return

    log_sync("INFO", f"Starting monitoring - Interface: {interface} MAC: {mac_address}")

    inotify = Inotify()
    inotify.add_watch(CONFIG['FILE_TO_MONITOR'])
    
    last_check = time.time()

    try:
        while True:
            # Process inotify events
            for event in inotify.event_gen(timeout=1):
                if event is not None:
                    _, type_names, path, filename = event
                    if 'IN_MODIFY' in type_names:
                        log_sync("INFO", "File modification detected", filename)
                        if send_to_server(CONFIG['FILE_TO_MONITOR'], mac_address):
                            update_state()

            # Periodic check every hour
            if time.time() - last_check > CONFIG['CHECK_INTERVAL']:
                if should_send_interval():
                    log_sync("INFO", "Periodic sync triggered")
                    if send_to_server(CONFIG['FILE_TO_MONITOR'], mac_address):
                        update_state()
                last_check = time.time()

    except KeyboardInterrupt:
        log_sync("INFO", "Monitoring stopped by user")
    finally:
        inotify.remove_watch(CONFIG['FILE_TO_MONITOR'])

if __name__ == "__main__":
    main()
