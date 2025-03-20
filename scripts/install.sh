#!/bin/bash

# Create virtual environment
#VENV_DIR="${PWD}/venv"
#python3 -m venv ${VENV_DIR}
#source ${VENV_DIR}/bin/activate
cd /home/pi/YUMI_SYNC
sudo rm -rf venv
python3 -m venv venv
source venv/bin/activate

# Install Python packages in venv
pip install --upgrade pip
pip install requests netifaces inotify-simple #python-inotify




# Create systemd service
sudo tee /etc/systemd/system/yumi-sync.service > /dev/null <<EOL
[Unit]
Description=YUMI Sync Service
After=network.target

[Service]
ExecStart=/home/pi/YUMI_SYNC/venv/bin/python /home/pi/YUMI_SYNC/yumi_sync//yumi_sync.py
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

cat <<EOL > /home/pi/printer_data/config/update_YUMI_SYNC.cfg
# YUMI_SYNC update_manager entry 
[update_manager YUMI_SYNC]
type: git_repo
path: ~/YUMI_SYNC
origin: https://github.com/Yumi-Lab/YUMI_SYNC.git
primary_branch: main
managed_services: YUMI_SYNC
install_script: scripts/install.sh
EOL

sudo chmod 777 /home/pi/printer_data/config/update_YUMI_SYNC.cfg

CONFIG_FILE="/home/pi/printer_data/config/moonraker.conf"
INCLUDE_LINE="[include update_YUMI_SYNC.cfg]"

# Vérifier si la ligne existe déjà
if ! grep -Fxq "$INCLUDE_LINE" "$CONFIG_FILE"; then
    echo "$INCLUDE_LINE" | sudo tee -a "$CONFIG_FILE" > /dev/null
    echo "Ligne ajoutée à $CONFIG_FILE"
else
    echo "La ligne existe déjà dans $CONFIG_FILE"
fi
echo "YUMI_SYNC" | sudo tee -a /home/pi/printer_data/moonraker.asvc


# Vérification de l'état du service
if systemctl is-active --quiet yumi-sync; then
    echo "✅ Installation complète. Service YUMI_SYNC en cours d'exécution."
else
    echo "❌ Erreur : Le service YUMI_SYNC ne s'est pas lancé correctement."
    journalctl -u yumi-sync --no-pager -n 20  # Afficher les 20 dernières erreurs
fi

echo "Installation complete. Service is running."
