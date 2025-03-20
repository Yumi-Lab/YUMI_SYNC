#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import requests
import hashlib
import json
from datetime import datetime, timedelta
import netifaces

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
server_url = "http://adb528.online-server.cloud/route_testing"

previous_hash = None

def calculate_file_hash(file_path):
    try:
        with open(file_path, 'rb') as file:
            return hashlib.md5(file.read()).hexdigest()
    except Exception as e:
        print(f"Error calculating file hash: {e}")
        return None

def send_file_to_server(file_path, timestamp, mac_address):
    try:
        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file)}
            data = {
                'timestamp': timestamp,                'mac_address': mac_address
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
            mac_address = get_mac_address(active_interface)
            if mac_address:
                send_file_to_server(file_to_monitor, timestamp, mac_address)
                save_current_hash(current_hash)
            else:
                print("Failed to get the MAC address.")
        previous_hash = current_hash

        last_sent_date = load_last_sent_date()
        if last_sent_date is None or (datetime.now() - datetime.strptime(last_sent_date, "%Y-%m-%d")).days >= 30:
            print("Sending the file as it has been 30 days or more...")
            timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
            mac_address = get_mac_address(active_interface)
            if mac_address:
                send_file_to_server(file_to_monitor, timestamp, mac_address)
                save_current_hash(current_hash)
                save_last_sent_date(time.strftime("%Y-%m-%d"))
            else:
                print("Failed to get the MAC address.")

        time.sleep(5)
    except KeyboardInterrupt:
        print("Monitoring stopped.")
        break
    except Exception as e:
        print(f"Error in monitoring: {e}")
