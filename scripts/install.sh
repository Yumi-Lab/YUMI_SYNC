#!/usr/bin/env bash
set -e
# Debug
set -x

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
    fi
}

install_dependencies() {
    apt-get update --allow-releaseinfo-change
    # shellcheck disable=SC2086
    apt-get install --yes ${PKGLIST#}
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
    cat > "${SERVICE_FILE_PATH}" << EOF
[Unit]
Description=Yumi Sync Service
Requires=network-online.target
After=network-online.target

[Service]
Type=simple
ExecStart=${PWD}/venv/bin/python ${PWD}/yumi_sync/yumi_sync.py
WorkingDirectory=/home/${BASE_USER}/YUMI_SYNC
Restart=always
User=${BASE_USER}

[Install]
WantedBy=multi-user.target

EOF
}

install_service() {
    printf "Install Yumi Sync service ..."
    create_service_file
}

if [[ "${BASH_SOURCE[0]}" = "${0}" ]]; then
    main "${@}"
fi
