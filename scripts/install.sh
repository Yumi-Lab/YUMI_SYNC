#!/usr/bin/env bash
set -e
# Debug
set -x

main() {
    if ! get_python_version; then
        install_python
    fi
}

py_not_installed_msg() {
    printf "ERROR: Python seem not to be installed on your System!\n"
    py_install_hint
}

py3_not_installed_msg() {
    printf "ERROR: Your Python version too old! At least version 3 is required!\n"
    py_install_hint
}

py_install_hint() {
    printf "Trying to install Python3'\n"
}

install_python() {
    sudo apt-get update --yes --allow-releaseinfo-change
    sudo apt-get install --yes python3
}

get_python_version() {
    local major version py_bin
    py_bin="$(which python 2>/dev/null)"
    if [[ -z "${py_bin}" ]]; then
        py_not_installed_msg
        return 1
    else
        version="$("${py_bin}" --version)"
        major="$(cut -f2 -d" " <<< "${version}" | cut -f1 -d".")"
        if [[ "${major}" -lt 5 ]]; then
            py3_not_installed_msg
            return 1
        else
            return 0
        fi
    fi
}


if [[ "${BASH_SOURCE[0]}" = "${0}" ]]; then
    main
fi
