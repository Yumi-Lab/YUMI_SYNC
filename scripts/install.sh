#!/usr/bin/env bash
set -e
# Debug
set -x

PKGLIST="python3 python3-venv"

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
        exit 0
    else
        install_dependencies
        create_virtualenv
    fi
}

install_dependencies() {
    sudo apt-get update --allow-releaseinfo-change
    # shellcheck disable=SC2086
    sudo apt-get install --yes ${PKGLIST#}
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

if [[ "${BASH_SOURCE[0]}" = "${0}" ]]; then
    main "${@}"
fi
