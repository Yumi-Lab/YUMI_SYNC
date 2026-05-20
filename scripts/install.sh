#!/usr/bin/env bash
#set -e
# Debug
set -x

PKGLIST="python3 python3-venv"
SERVICE_FILE_PATH="/etc/systemd/system/yumi_sync.service"
INSTALL_DIR="/home/pi/YUMI_SYNC"

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
    systemctl daemon-reload
    printf "Enable Yumi Sync Service ...\n"
    systemctl enable "$(basename "${SERVICE_FILE_PATH}")"
    printf "Start Yumi Sync Service ...\n"
    systemctl restart "$(basename "${SERVICE_FILE_PATH}")"
}

generate_moonraker_update() {
    local config_file="/home/pi/printer_data/config/update_yumi_sync.cfg"
    # Remove old filename if exists
    if [[ -f "/home/pi/printer_data/config/update_YUMI_SYNC.cfg" ]]; then
        rm "/home/pi/printer_data/config/update_YUMI_SYNC.cfg"
    fi
    cat <<EOL > "${config_file}"
[update_manager yumi_sync]
type: git_repo
path: ~/YUMI_SYNC
origin: https://github.com/Yumi-Lab/YUMI_SYNC.git
primary_branch: main
managed_services: yumi_sync
requirements: requirements.txt
system_dependencies: system_dependencies.json
EOL
    chmod 644 "${config_file}"
}

generate_moonraker_asvc() {
    CONFIG_FILE="/home/pi/printer_data/config/moonraker.conf"
    INCLUDE_LINE="[include update_yumi_sync.cfg]"
    # Remove old include if present
    sed -i '/include update_YUMI_SYNC.cfg/d' "$CONFIG_FILE"

    if ! grep -Fxq "$INCLUDE_LINE" "$CONFIG_FILE"; then
        echo "$INCLUDE_LINE" | sudo tee -a "$CONFIG_FILE" > /dev/null
        echo "Ligne ajoutée à $CONFIG_FILE"
    else
        echo "La ligne existe déjà dans $CONFIG_FILE"
    fi

    echo "yumi_sync" | sudo tee -a /home/pi/printer_data/moonraker.asvc
}

fix_symlink() {
    TARGET_SCRIPT="/home/pi/YUMI_SYNC/yumi_sync/yumi_sync.py"
    ln -sf "$TARGET_SCRIPT" /usr/local/bin/YUMI_SYNC
    # Don't chmod the symlink target — it dirties the git repo
    # The venv python handles execution directly

    if [[ ! -L /usr/local/bin/YUMI_SYNC ]]; then
        echo "YUMI_SYNC symlink not created."
        exit 1
    else
        echo "YUMI_SYNC installed and accessible as system command."
    fi
}

install_id_klipperscreen() {
    cp /home/pi/YUMI_SYNC/scripts/Config//base_panel.py /home/pi/KlipperScreen/panels/base_panel.py
}

# Reset any permission changes that dirty the git repo
cleanup_git() {
    pushd "${INSTALL_DIR}" &>/dev/null || return
    git checkout . 2>/dev/null || true
    popd &>/dev/null || return
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
        cleanup_git
    fi
}

if [[ "${BASH_SOURCE[0]}" = "${0}" ]]; then
    main "${@}"
fi
