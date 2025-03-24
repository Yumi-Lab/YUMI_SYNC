#!/usr/bin/env bash
set -e
# Debug
#set -x


PKGLIST="python3 python3-venv"
SERVICE_FILE_PATH="/etc/systemd/system/yumi_sync.service"
INSTALL_DIR="/home/pi/YUMI_SYNC"  # Répertoire d'installation par défaut

# Détection de l'utilisateur de base
[[ -n $BASE_USER ]] || BASE_USER="$(whoami)"
[[ "${BASE_USER}" = "root" ]] && BASE_USER="${SUDO_USER}"
[[ -n "${BASE_USER}" ]] || { echo "Error: BASE_USER is not defined."; exit 1; }

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
        add_moonraker_update
        generate_moonraker_asvc
        fix_symlink
    fi
}

install_dependencies() {
    apt-get update --allow-releaseinfo-change
    # shellcheck disable=SC2086
    apt-get install --yes ${PKGLIST}
}

create_virtualenv() {
    local py_bin
    py_bin="$(which python3)"
    printf "Creating virtual environment ...\n"
    "${py_bin}" -m venv "${INSTALL_DIR}/venv"
    printf "Install requirements ...\n"
    
    if [[ ! -f "${INSTALL_DIR}/requirements.txt" ]]; then
        echo "requirements.txt not found, skipping package installation."
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
# Commenter cette ligne si elle provoque un délai ou réduisez le temps de sommeil
# ExecStartPre=/bin/sleep 10
ExecStart=${INSTALL_DIR}/venv/bin/python ${INSTALL_DIR}/yumi_sync/yumi_sync.py
WorkingDirectory=${INSTALL_DIR}
Restart=always
User=${BASE_USER}
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF
}

install_service() {
    printf "Install Yumi Sync service ...\n"
    create_service_file
    printf "Enable Yumi Sync Service ...\n"
    systemctl enable "$(basename "${SERVICE_FILE_PATH}")"
    printf "Start Yumi Sync Service ...\n"
    systemctl start "$(basename "${SERVICE_FILE_PATH}")"
}

add_moonraker_update() {
    local config_dir conf_file_src conf_file_ln
    config_dir="/home/${BASE_USER}/printer_data/config"
    conf_file_src="${INSTALL_DIR}/yumi_sync-update.conf"
    conf_file_ln="${config_dir}/yumi_sync-update.conf"
    
    if [[ -d "${config_dir}" ]]; then
        if [[ -L "${conf_file_ln}" ]]; then
            echo "Link already exists: ${conf_file_ln}"
        else
            ln -s "${conf_file_src}" "${conf_file_ln}"
        fi
    fi

    if [[ -f "${config_dir}/moonraker.conf" ]]; then
        if ! grep -q "\[include yumi_sync-update.conf\]" "${config_dir}/moonraker.conf"; then
            echo "[include yumi_sync-update.conf]" >> "${config_dir}/moonraker.conf"
        fi
    fi
}


add_moonraker_update() {
#update service moonraker
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

sudo chmod 644 /home/pi/printer_data/config/update_YUMI_SYNC.cfg
}

generate_moonraker_asvc() {
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

    # Lancement du script principal
    if [[ "${BASH_SOURCE[0]}" = "${0}" ]]; then
        main "${@}"
    fi
}

fix_symlink() {
    # === Corriger le lien vers la commande YUMI_SYNC ===

# Chemin vers le script Python à exécuter
TARGET_SCRIPT="/home/pi/YUMI_SYNC/yumi_sync/yumi_sync.py"

# Lien symbolique global pour utiliser la commande YUMI_SYNC dans tout le système
ln -sf "$TARGET_SCRIPT" /usr/local/bin/YUMI_SYNC
chmod +x /usr/local/bin/YUMI_SYNC

# Vérifie que la commande est bien accessible globalement
if [[ ! -x "$(command -v YUMI_SYNC)" ]]; then
    echo "❌ YUMI_SYNC n’est toujours pas accessible en tant que commande système."
    exit 1
else
    echo "✅ YUMI_SYNC installé et accessible via la commande système."
fi
}
