#!/bin/bash

# Create virtual environment
VENV_DIR="${PWD}/venv"
python3 -m venv ${VENV_DIR}
source ${VENV_DIR}/bin/activate

# Install Python packages in venv
pip install --upgrade pip
pip install requests netifaces inotify-simple #python-inotify




# Create systemd service
sudo tee /etc/systemd/system/yumi-sync.service > /dev/null <<EOL
[Unit]
Description=YUMI Sync Service
After=network.target

[Service]
ExecStart=${VENV_DIR}/bin/python ${PWD}/yumi_sync.py
Restart=always
Environment=SYNC_SERVER=https://sync.yumi-lab.com/route_testing
Environment=MONITOR_FILE=/home/pi/printer_data/config/printer.cfg
WorkingDirectory=${PWD}
User=pi

[Install]
WantedBy=multi-user.target
EOL

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable yumi-sync
sudo systemctl start yumi-sync

# Vérification de l'état du service
if systemctl is-active --quiet yumi-sync; then
    echo "✅ Installation complète. Service YUMI_SYNC en cours d'exécution."
else
    echo "❌ Erreur : Le service YUMI_SYNC ne s'est pas lancé correctement."
    journalctl -u yumi-sync --no-pager -n 20  # Afficher les 20 dernières erreurs
fi

echo "Installation complete. Service is running."
