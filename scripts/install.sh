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
}

rebuild_venv() {
    if [[ -d "${venv}" ]]; then
        rm -f "${PWD}/venv"
    fi
    create_virtualenv
}

if [[ "${BASH_SOURCE[0]}" = "${0}" ]]; then
    main "${@}"
fi
