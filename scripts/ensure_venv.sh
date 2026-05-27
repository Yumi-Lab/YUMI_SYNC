#!/bin/bash
# Ensure YUMI_SYNC venv exists and has dependencies installed
# Called by systemd ExecStartPre or manually

INSTALL_DIR="/home/pi/YUMI_SYNC"
VENV_DIR="${INSTALL_DIR}/venv"
VENV_PYTHON="${VENV_DIR}/bin/python"
SERVICE_FILE="/etc/systemd/system/yumi_sync.service"

# 1. Recreate venv if missing
if [ ! -f "${VENV_PYTHON}" ]; then
    echo "[ensure_venv] venv missing, creating..."
    python3 -m venv "${VENV_DIR}"
    "${VENV_DIR}/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"
    echo "[ensure_venv] venv created"
else
    # 1b. Venv exists — ensure all dependencies are installed
    # (handles new deps added to requirements.txt after git pull)
    "${VENV_DIR}/bin/pip" install --quiet -r "${INSTALL_DIR}/requirements.txt" 2>/dev/null
fi

# 2. Fix service file if it still points to wrong python or missing ExecStartPre
if ! grep -q "ExecStartPre" "${SERVICE_FILE}" 2>/dev/null; then
    echo "[ensure_venv] Updating service file with ExecStartPre..."
    sed -i "s|^ExecStart=.*|ExecStartPre=/bin/bash ${INSTALL_DIR}/scripts/ensure_venv.sh\nExecStart=${VENV_PYTHON} ${INSTALL_DIR}/yumi_sync/yumi_sync.py|" "${SERVICE_FILE}"
    systemctl daemon-reload
    echo "[ensure_venv] Service file updated"
fi
