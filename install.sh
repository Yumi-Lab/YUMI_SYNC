#!/bin/bash
#set -x

# Vérifiez si le script est exécuté avec sudo et déterminez l'utilisateur réel
if [ ! -z "$SUDO_USER" ]; then
    REAL_USER="$SUDO_USER"
else
    REAL_USER="$(whoami)"
fi
echo "Utilisateur réel: $REAL_USER"

# Utilisez getent pour obtenir le chemin du répertoire personnel de l'utilisateur réel
USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
echo "Répertoire personnel de l'utilisateur: $USER_HOME"

# Define paths for the script, the systemd service file, and the moonraker.conf file
SCRIPT_PATH="/home/pi/YUMI_SYNC/yumi_sync.py"
SERVICE_PATH="/etc/systemd/system/yumi_sync.service"
REPO_DIR="/home/pi/YUMI_SYNC"
MOONRAKER_CONF="/home/pi/printer_data/config/moonraker.conf"
MOONRAKER_CONF_FOLDER="/home/pi/printer_data/config"
INSTALL_SCRIPT_PATH="/home/pi/YUMI_SYNC/install.sh"
VIRTUALENV_PATH="/home/pi/YUMI_SYNC/virtualenv"

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

# Create and activate the virtual environment using virtualenv
if [ ! -d "$VIRTUALENV_PATH" ]; then
    echo "Creating virtual environment..."
    virtualenv -p python3 "$VIRTUALENV_PATH"
fi
source "$VIRTUALENV_PATH/bin/activate"

# Ensure the script Python is executable
sudo chmod +x "$SCRIPT_PATH"

# Install dependencies
pip install netifaces requests

# Check if python3 is installed
if command -v python3 &>/dev/null; then
    echo "python3 is installed"
else
    echo "python3 is not installed. Please run the following command to install it:"
    echo "sudo apt-get install python3"
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
ExecStart=$VIRTUALENV_PATH/bin/python $SCRIPT_PATH
WorkingDirectory=/home/pi/YUMI_SYNC
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOL

if [ -f "$MOONRAKER_CONF" ]; then
   
    # Check if the string [include yumi_sync.cfg] is already present in the file
    if ! grep -Fq '[include yumi_sync.cfg]' "$MOONRAKER_CONF"; then
        echo "Adding the string [include yumi_sync.cfg] to the moonraker.conf file..."
        # Create a temporary file
        temp_file=$(mktemp)

        # Add the line [include yumi_sync.cfg] to the beginning of the temporary file
        echo "[include yumi_sync.cfg]" > "$temp_file"

        # Concatenate the content of the existing moonraker.conf file with the temporary file
        cat "$MOONRAKER_CONF" >> "$temp_file"

        # Replace the existing moonraker.conf file with the temporary file
        mv "$temp_file" "$MOONRAKER_CONF"

        # Check if the string was added successfully
        if grep -Fq '[include yumi_sync.cfg]' "$MOONRAKER_CONF"; then
            echo "The string [include yumi_sync.cfg] was added successfully to the moonraker.conf file."
        else
            echo "Error: the string [include yumi_sync.cfg] was not added to the moonraker.conf file."
        fi
    else
        echo "The string [include yumi_sync.cfg] is already present in the moonraker.conf file."
    fi

    # give moonraker permitted to restart service
    # Check if the moonraker.asvc file exists
    if [ ! -f /home/pi/printer_data/moonraker.asvc ]; then
        echo "The moonraker.asvc file does not exist, creating the file..."
        touch /home/pi/printer_data/moonraker.asvc
    fi

    # Check if the string # give moonraker permitted to restart service is already present in the file
    if grep -Fq "# give moonraker permitted to restart service" /home/pi/printer_data/moonraker.asvc; then
        echo "The string # give moonraker permitted to restart service is already present in the moonraker.asvc file."
    else
        echo "Adding the string # give moonraker permitted to restart service to the moonraker.asvc file..."
        # Create a temporary file
        temp_file=$(mktemp)

        # Add the line # give moonraker permitted to restart service to the beginning of the file
        echo "# give moonraker permitted to restart service" > "$temp_file"
        cat /home/pi/printer_data/moonraker.asvc >> "$temp_file"

        # Replace the original file with the temporary file
        mv "$temp_file" /home/pi/printer_data/moonraker.asvc
    fi

    # Add the string "yumi_sync" to the second line of the file
    if grep -Fq "yumi_sync" /home/pi/printer_data/moonraker.asvc; then
        echo "The string yumi_sync is already present in the moonraker.asvc file."
    else
        echo "Adding the string yumi_sync to the moonraker.asvc file..."
        # Create a temporary file
        temp_file=$(mktemp)

        # Copy the first line of the original file to the temporary file
        head -n 1 /home/pi/printer_data/moonraker.asvc > "$temp_file"

        # Add the string "yumi_sync" to the second line of the temporary file
        echo -n "yumi_sync" $'\n' >> "$temp_file"

        # Concatenate the rest of the original file with the temporary file
        tail -n +2 /home/pi/printer_data/moonraker.asvc >> "$temp_file"

        # Replace the original file with the temporary file
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

    # Cette commande change le propriétaire et le groupe récursivement
    # de tous les fichiers et répertoires situés dans $USER_HOME/printer_data/config/
    # pour qu'ils appartiennent à l'utilisateur 'pi' et au groupe 'pi'.
    sudo chown -R pi:pi $USER_HOME/printer_data/config/

    # Vérification après le changement de propriétaire et de groupe
    if [ "$(stat -c '%U:%G' $USER_HOME/printer_data/config/)" = "pi:pi" ]; then
        echo "La vérification du changement de propriétaire et de groupe a réussi."
    else
        echo "Erreur : Le changement de propriétaire et de groupe n'a pas abouti."
    fi


    echo "Installation completed."
fi
