#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import requests
import hashlib
import json
import logging
from datetime import datetime
import netifaces

# === CONFIGURATION DU LOG ===
logging.basicConfig(
    filename='/var/log/yumi_sync.log',
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

file_to_monitor = '/home/pi/printer_data/config/printer.cfg'
state_file_path = '/home/pi/monitoring_state.json'
server_url = "http://yumi-id.yumi-lab.com/route_testing"

# Forcer l'utilisation de l'interface Ethernet (RJ45)
FORCED_INTERFACE = 'end0'

def get_mac_address(interface_name):
    try:
        iface = netifaces.ifaddresses(interface_name)[netifaces.AF_LINK]
        return iface[0]['addr']
    except KeyError:
        logging.error(f"MAC address not found for {interface_name}")
        return None

active_interface = FORCED_INTERFACE
mac_address = get_mac_address(active_interface)

if mac_address:
    logging.info(f"MAC address of {active_interface}: {mac_address}")
else:
    logging.error("MAC address not found.")

previous_hash = None

def calculate_file_hash(file_path):
    try:
        with open(file_path, 'rb') as file:
            return hashlib.md5(file.read()).hexdigest()
    except Exception as e:
        logging.error(f"Error calculating file hash: {e}")
        return None

def send_file_to_server(file_path, timestamp, mac_address):
    try:
        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file)}
            data = {'timestamp': timestamp, 'mac_address': mac_address}
            response = requests.post(server_url, data=data, files=files)

            if response.status_code == 200:
                logging.info("? File successfully sent to server.")
            else:
                logging.error(f"? Server error {response.status_code} during file send.")
    except Exception as e:
        logging.error(f"Exception while sending file: {e}")

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
            logging.info("?? Detected printer.cfg change. Sending to server...")
            timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
            if mac_address:
                send_file_to_server(file_to_monitor, timestamp, mac_address)
                save_current_hash(current_hash)
            else:
                logging.error("MAC address unavailable. Cannot send file.")
        previous_hash = current_hash

        last_sent_date = load_last_sent_date()
        if last_sent_date is None or (datetime.now() - datetime.strptime(last_sent_date, "%Y-%m-%d")).days >= 30:
            logging.info("?? 30 days passed. Sending file as scheduled.")
            timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
            if mac_address:
                send_file_to_server(file_to_monitor, timestamp, mac_address)
                save_current_hash(current_hash)
                save_last_sent_date(time.strftime("%Y-%m-%d"))
            else:
                logging.error("MAC address unavailable. Cannot send file.")

        time.sleep(5)
    except KeyboardInterrupt:
        logging.info("?? Monitoring stopped by user.")
        break
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
