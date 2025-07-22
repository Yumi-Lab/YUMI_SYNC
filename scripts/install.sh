#!/usr/bin/env bash
#set -e
# Debug
set -x

PKGLIST="python3 python3-venv"
SERVICE_FILE_PATH="/etc/systemd/system/yumi_sync.service"
INSTALL_DIR="/home/pi/YUMI_SYNC"  # Répertoire d'installation par défaut

# Détection de l'utilisateur de base
if [[ -n "$SUDO_USER" ]]; then
    BASE_USER="$SUDO_USER"
else
    BASE_USER="$(whoami)"
fi
[[ -n "${BASE_USER}" ]] || { echo "Error: BASE_USER is not defined."; exit 1; }

install_dependencies() {
    apt-get update --allow-releaseinfo-change
    apt-get install --yes ${PKGLIST}
    apt-get install --yes python3-pip
    sudo apt install python3-venv -y
    python3 -m venv /home/pi/yumi_venv
    source /home/pi/yumi_venv/bin/activate
    pip install requests netifaces
    sudo touch /home/pi/monitoring_state.json
    sudo chown pi:pi /home/pi/monitoring_state.json
}

create_virtualenv() {
    local py_bin
    py_bin="$(which python3)"
    printf "Creating virtual environment ...\n"
    "${py_bin}" -m venv "${INSTALL_DIR}/venv"
    printf "Installing required Python packages ...\n"

    "${INSTALL_DIR}/venv/bin/pip" install requests netifaces

    if [[ ! -f "${INSTALL_DIR}/requirements.txt" ]]; then
        echo "requirements.txt not found, skipping additional package installation."
        return
    fi

    if [[ "$(uname -m)" =~ armv[67]l ]]; then
        "${INSTALL_DIR}/venv/bin/pip" install --extra-index-url https://www.piwheels.org/simple -r "${INSTALL_DIR}/requirements.txt"
    else
        "${INSTALL_DIR}/venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"
    fi
}

rebuild_venv() {
    if [[ -d "${INSTALL_DIR}/venv" ]]; then
        printf "Removing old virtual environment...\n"
        rm -rf "${INSTALL_DIR}/venv"
    fi
    create_virtualenv
}

create_service_file() {
    cat << EOF > "${SERVICE_FILE_PATH}"
[Unit]
Description=Yumi Sync Service
Requires=network-online.target
After=network-online.target

[Service]
Type=simple
# ExecStartPre=/bin/sleep 10
ExecStart=${INSTALL_DIR}/venv/bin/python ${INSTALL_DIR}/yumi_sync/yumi_sync.py
WorkingDirectory=${INSTALL_DIR}
Restart=always
User=${BASE_USER}
TimeoutStartSec=300
StandardOutput=append:/var/log/yumi_sync.log
StandardError=append:/var/log/yumi_sync.log

[Install]
WantedBy=multi-user.target
EOF
    touch /var/log/yumi_sync.log
    chown "${BASE_USER}:${BASE_USER}" /var/log/yumi_sync.log
    chmod 644 /var/log/yumi_sync.log
}

install_service() {
    printf "Install Yumi Sync service ...\n"
    create_service_file
    printf "Enable Yumi Sync Service ...\n"
    systemctl enable "$(basename "${SERVICE_FILE_PATH}")"
    printf "Start Yumi Sync Service ...\n"
    systemctl restart "$(basename "${SERVICE_FILE_PATH}")"
}

generate_moonraker_update() {
    local config_file="/home/pi/printer_data/config/update_YUMI_SYNC.cfg"
    cat <<EOL > "${config_file}"
# YUMI_SYNC update_manager entry 
[update_manager YUMI_SYNC]
type: git_repo
path: ~/YUMI_SYNC
origin: https://github.com/Yumi-Lab/YUMI_SYNC.git
primary_branch: main
managed_services: YUMI_SYNC
install_script: scripts/install.sh
EOL
    chmod 644 "${config_file}"
}

generate_moonraker_asvc() {
    CONFIG_FILE="/home/pi/printer_data/config/moonraker.conf"
    INCLUDE_LINE="[include update_YUMI_SYNC.cfg]"

    if ! grep -Fxq "$INCLUDE_LINE" "$CONFIG_FILE"; then
        echo "$INCLUDE_LINE" | sudo tee -a "$CONFIG_FILE" > /dev/null
        echo "Ligne ajoutée à $CONFIG_FILE"
    else
        echo "La ligne existe déjà dans $CONFIG_FILE"
    fi

    echo "YUMI_SYNC" | sudo tee -a /home/pi/printer_data/moonraker.asvc
}

fix_symlink() {
    TARGET_SCRIPT="/home/pi/YUMI_SYNC/yumi_sync/yumi_sync.py"
    ln -sf "$TARGET_SCRIPT" /usr/local/bin/YUMI_SYNC
    chmod +x /usr/local/bin/YUMI_SYNC

    if [[ ! -x "$(command -v YUMI_SYNC)" ]]; then
        echo "❌ YUMI_SYNC n’est toujours pas accessible en tant que commande système."
        exit 1
    else
        echo "✅ YUMI_SYNC installé et accessible via la commande système."
    fi
}

install_id_klipperscreen() {
        cp /home/pi/YUMI_SYNC/Config/base_panel.py /home/pi/KlipperScreen/panels/base_panel.py
}

main() {
    local rebuildvenv
    case "${@}" in
        -r|--rebuildvenv)
            rebuildvenv="true"
        ;;
        *)
        ;;
    esac
    if [[ "${rebuildvenv}" = "true" ]]; then
        rebuild_venv
        printf "Rebuilding virtual environment done!\n"
        exit 0
    else
        install_dependencies
        create_virtualenv
        install_service
        generate_moonraker_update
        generate_moonraker_asvc
        fix_symlink
        install_id_klipperscreen
    fi
}

# Lancement
if [[ "${BASH_SOURCE[0]}" = "${0}" ]]; then
    main "${@}"
fi
