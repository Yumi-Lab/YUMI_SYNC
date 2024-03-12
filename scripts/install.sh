#!/bin/bash
#set -x

# Define paths for the script, the systemd service file, and the moonraker.conf file
SCRIPT_PATH="/home/pi/YUMI_SYNC/yumi_sync.py"
SERVICE_PATH="/etc/systemd/system/yumi_sync.service"
REPO_URL="https://github.com/Yumi-Lab/YUMI-SYNC.git"
REPO_DIR="/home/pi/YUMI_SYNC"
MOONRAKER_CONF="/home/pi/printer_data/config/moonraker.conf"
MOONRAKER_CONF_FOLDER="/home/pi/printer_data/config"
INSTALL_SCRIPT_PATH="/home/pi/YUMI_SYNC/install.sh"

# Check if the installation directory exists, if not, create it
#if [ ! -d "/home/pi/YUMI_SYNC" ]; then
#    mkdir -p /home/pi/YUMI_SYNC
#fi

# Clone or update the repository to the latest version
#if [ ! -d "$REPO_DIR" ]; then
#    git clone "$REPO_URL" "$REPO_DIR"
#else
#    git -C "$REPO_DIR" pull
#fi

# Ensure the script Python is executable
sudo chmod +x "$SCRIPT_PATH"

# Vérifier si python3 est installé
if command -v python3 &>/dev/null; then
    echo "python3 est installé"
else
    echo "python3 n'est pas installé. Veuillez exécuter la commande suivante pour l'installer :"
    echo "sudo apt-get install python3"
    exit 1
fi

# Vérifier si netifaces est installé
if python3 -c "import netifaces" &>/dev/null; then
    echo "netifaces est installé"
else
    echo "netifaces n'est pas installé. Veuillez exécuter la commande suivante pour l'installer :"
    echo "sudo apt-get install python3-netifaces"
    exit 1
fi

# Vérifier si pip est installé
if command -v pip > /dev/null 2>&1; then
    echo "pip est installé"
else
    echo "pip n'est pas installé. Veuillez exécuter la commande suivante pour l'installer :"
    echo "sudo apt update && sudo apt install -y python3-pip"
    exit 1
fi

# Vérifier si requests est installé
if pip3 list | grep -q requests; then
    echo "requests est installé"
else
    echo "requests n'est pas installé. Veuillez exécuter la commande suivante pour l'installer :"
    echo "pip3 install requests"
    exit 1
fi


# Check if netifaces is installed, if not, install it
if ! python3 -c "import netifaces" &>/dev/null; then
    echo "netifaces is not installed."
else
    echo "netifaces is installed."
fi

# Create the systemd service file
cat > "$SERVICE_PATH" <<EOL
[Unit]
Description=Yumi Sync Service

[Service]
ExecStart=/usr/bin/python3 $SCRIPT_PATH
WorkingDirectory=/home/pi/YUMI_SYNC
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOL


if [ -f "$MOONRAKER_CONF" ]; then
    MOONRAKER_CONF="/home/pi/printer_data/config/moonraker.conf"

# Vérifier si la chaîne [include yumi_sync.cfg] est déjà présente dans le fichier
    if ! grep -Fq '[include yumi_sync.cfg]' "$MOONRAKER_CONF"; then
    echo "Ajout de la chaîne [include yumi_sync.cfg] au fichier moonraker.conf..."
    # Créer un fichier temporaire
    temp_file=$(mktemp)

    # Ajouter la ligne [include yumi_sync.cfg] au début du fichier temporaire
    echo "[include yumi_sync.cfg]" > "$temp_file"

    # Concaténer le contenu du fichier moonraker.conf existant avec le fichier temporaire
    cat "$MOONRAKER_CONF" >> "$temp_file"

    # Remplacer le fichier moonraker.conf existant par le fichier temporaire
    mv "$temp_file" "$MOONRAKER_CONF"

    # Vérifier si la chaîne a été ajoutée avec succès
    if grep -Fq '[include yumi_sync.cfg]' "$MOONRAKER_CONF"; then
        echo "La chaîne [include yumi_sync.cfg] a été ajoutée avec succès au fichier moonraker.conf."
    else
        echo "Erreur : la chaîne [include yumi_sync.cfg] n'a pas été ajoutée au fichier moonraker.conf."
    fi
    else
    echo "La chaîne [include yumi_sync.cfg] est déjà présente dans le fichier moonraker.conf."
    fi


# check if yumi_sync.cfg exist, delete if exist, and create a new one
if [ -f /home/pi/printer_data/config/yumi_sync.cfg ]; then
    echo "The file /home/pi/printer_data/config/yumi_sync.cfg was already created. Deleting it..."
    rm /home/pi/printer_data/config/yumi_sync.cfg
else
    echo "The file /home/pi/printer_data/config/yumi_sync.cfg was not found. Creating it..."
fi

cat > /home/pi/printer_data/config/yumi_sync.cfg <<EOF
[update_manager yumi_sync]
type: git_repo
path: ~/YUMI_SYNC
origin: https://github.com/Yumi-Lab/YUMI-SYNC.git
primary_branch: main
managed_services: yumi_sync
install_script: $INSTALL_SCRIPT_PATH
EOF

# check if yumi_sync.cfg was created successfully
if [ -f /home/pi/printer_data/config/yumi_sync.cfg ]; then
    echo "The file /home/pi/printer_data/config/yumi_sync.cfg has been created successfully."
else
    echo "Error: The file /home/pi/printer_data/config/yumi_sync.cfg was not created."
fi

# give moonraker permitted to restart service
# Vérifier si le fichier moonraker.asvc existe
if [ ! -f /home/pi/printer_data/moonraker.asvc ]; then
    echo "Le fichier moonraker.asvc n'existe pas, création du fichier..."
    touch /home/pi/printer_data/moonraker.asvc
fi

# Vérifier si la chaîne # give moonraker permitted to restart service est déjà présente dans le fichier
if grep -Fq "# give moonraker permitted to restart service" /home/pi/printer_data/moonraker.asvc; then
    echo "La chaîne # give moonraker permitted to restart service est déjà présente dans le fichier moonraker.asvc."
else
    echo "Ajout de la chaîne # give moonraker permitted to restart service au fichier moonraker.asvc..."
    # Créer un fichier temporaire
    temp_file=$(mktemp)

    # Ajouter la ligne # give moonraker permitted to restart service au début du fichier
    echo "# give moonraker permitted to restart service" > "$temp_file"
    cat /home/pi/printer_data/moonraker.asvc >> "$temp_file"

    # Remplacer le fichier original par le fichier temporaire
    mv "$temp_file" /home/pi/printer_data/moonraker.asvc
fi

# Ajouter la chaîne "yumi_sync" à la deuxième ligne du fichier
if grep -Fq "yumi_sync" /home/pi/printer_data/moonraker.asvc; then
    echo "La chaîne yumi_sync est déjà présente dans le fichier moonraker.asvc."
else
    echo "Ajout de la chaîne yumi_sync au fichier moonraker.asvc..."
    # Créer un fichier temporaire
    temp_file=$(mktemp)

    # Copier la première ligne du fichier original dans le fichier temporaire
    head -n 1 /home/pi/printer_data/moonraker.asvc > "$temp_file"

    # Ajouter la chaîne "yumi_sync" à la deuxième ligne du fichier temporaire
    echo -n "yumi_sync" $'\n' >> "$temp_file"

    # Concaténer le reste du fichier original avec le fichier temporaire
    tail -n +2 /home/pi/printer_data/moonraker.asvc >> "$temp_file"

    # Remplacer le fichier original par le fichier temporaire
    mv "$temp_file" /home/pi/printer_data/moonraker.asvc
fi

# Reload systemd to recognize the changes
systemctl daemon-reload

# Start the service
systemctl start yumi_sync.service

# Check if the service is running
if systemctl is-active yumi_sync.service; then
    echo "The YUMI_SYNC service is running."
else
    echo "Error: The YUMI_SYNC service failed to start."
fi

# Enable the service to start on boot
systemctl enable yumi_sync.service

# Check if the service is enabled on boot
if systemctl is-enabled yumi_sync.service; then
    echo "The YUMI_SYNC service is enabled on boot."
else
    echo "Error: The YUMI_SYNC service failed to enable on boot."
fi

echo "Installation completed."
fi