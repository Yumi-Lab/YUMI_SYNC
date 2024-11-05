#!/usr/bin/env bash
set -e
# Debug
#set -x

PKGLIST="python3 python3-venv"

SERVICE_FILE_PATH="/etc/systemd/system/yumi_sync.service"

[[ -n $BASE_USER ]] || BASE_USER="$(whoami)"
[[ "${BASE_USER}" = "root" ]] && BASE_USER="${SUDO_USER}"

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
    "${py_bin}" -m venv "${PWD}/venv"
    printf "Install requirements ...\n"
    if [[ "$(uname -m)" =~ armv[67]l ]]; then
        "${PWD}"/venv/bin/pip install --extra-index-url https://www.piwheels.org/simple -r "${PWD}/requirements.txt"
    else
        "${PWD}"/venv/bin/pip install -r "${PWD}/requirements.txt"
    fi
}

rebuild_venv() {
    if [[ -d "${PWD}/venv" ]]; then
        printf "Removing old virtual environment...\n"
        rm -rf "${PWD}/venv"
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
ExecStart=/home/pi/YUMI_SYNC/venv/bin/python /home/pi/YUMI_SYNC/yumi_sync/yumi_sync.py
WorkingDirectory=/home/pi/YUMI_SYNC
Restart=always
User=pi
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
    if [[ ! -d  /proc ]]; then
        printf "Start Yumi Sync Service ...\n"
        systemctl start "$(basename "${SERVICE_FILE_PATH}")"
    fi
}

add_moonraker_update() {
    local config_dir conf_file_src conf_file_ln
    config_dir="/home/${BASE_USER}/printer_data/config"
    conf_file_src="${PWD}/yumi_sync-update.conf"
    conf_file_ln="${config_dir}/yumi_sync-update.conf"
    if [[ -d "${config_dir}" ]]; then
        ln -s "${conf_file_src}" "${conf_file_ln}"
    fi

    if [[ -f "${config_dir}/moonraker.conf" ]]; then
        echo "[include yumi_sync-update.conf]" >> "${config_dir}/moonraker.conf"
    fi
}

generate_moonraker_asvc() {
    local asset asvc
    asset="/home/${BASE_USER}/moonraker/moonraker/assets/default_allowed_services"
    asvc="/home/${BASE_USER}/printer_data/moonraker.asvc"
    if [[ -f "${asset}" ]]; then
        printf "Moonraker Repository found ...\n"
        cat "${asset}" > "${asvc}"
        echo "yumi_sync" >> "${asvc}"
        chown "${BASE_USER}":"${BASE_USER}" "${asvc}"
    fi
}

if [[ "${BASH_SOURCE[0]}" = "${0}" ]]; then
    main "${@}"
fi
