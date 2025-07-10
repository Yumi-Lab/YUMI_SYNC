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
    filename='/home/pi/printer_data/logs/yumi_sync.log',
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
        logging.error(f"❌ MAC address not found for {interface_name}")
        return None

mac_address = get_mac_address(FORCED_INTERFACE)

if mac_address:
    logging.info(f"✅ MAC address of {FORCED_INTERFACE}: {mac_address}")
else:
    logging.error("❌ MAC address not found. Arrêt du script.")
    exit(1)

def calculate_file_hash(file_path):
    try:
        with open(file_path, 'rb') as file:
            return hashlib.md5(file.read()).hexdigest()
    except Exception as e:
        logging.error(f"❌ Erreur de calcul du hash du fichier : {e}")
        return None

def send_file_to_server(file_path, timestamp, mac_address):
    try:
        hexid = mac_address.replace(":", "").upper()
        logging.info(f"📤 Modification détectée de printer.cfg. Envoi en cours... HEX = {hexid}")

        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file)}
            data = {'timestamp': timestamp, 'hexid': hexid}
            response = requests.post(server_url, data=data, files=files)

            if response.status_code == 200:
                logging.info("✅ Fichier envoyé avec succès au serveur.")
            else:
                logging.error(f"❌ Erreur serveur {response.status_code} pendant l'envoi.")
    except Exception as e:
        logging.error(f"❌ Exception lors de l'envoi du fichier : {e}")

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
        logging.error(f"❌ Impossible d'écrire dans le fichier state : {e}")

state = load_state()
previous_hash = state.get('last_hash')
last_sent_date = state.get('last_sent_date')

while True:
    try:
        current_hash = calculate_file_hash(file_to_monitor)
        today_str = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        # Envoi si changement de fichier
        if current_hash and current_hash != previous_hash:
            send_file_to_server(file_to_monitor, timestamp, mac_address)
            state['last_hash'] = current_hash
            state['last_sent_date'] = today_str
            save_state(state)
            previous_hash = current_hash
        # Envoi forcé tous les 30 jours
        elif last_sent_date is None or (datetime.now() - datetime.strptime(last_sent_date, "%Y-%m-%d")).days >= 30:
            logging.info("📅 30 jours écoulés. Envoi planifié du fichier.")
            send_file_to_server(file_to_monitor, timestamp, mac_address)
            state['last_hash'] = current_hash
            state['last_sent_date'] = today_str
            save_state(state)
            previous_hash = current_hash

        time.sleep(5)

    except KeyboardInterrupt:
        logging.info("🛑 Arrêt manuel du script.")
        break
    except Exception as e:
        logging.error(f"❌ Erreur inattendue dans la boucle principale : {e}")
