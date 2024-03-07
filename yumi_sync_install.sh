#!/bin/bash

# Verificar si pip3 está instalado
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 no está instalado. Instálalo ejecutando: sudo apt-get install python3-pip"
    exit 1
fi

# Instalar el módulo requests si no está instalado
if ! python3 -c "import requests" &> /dev/null; then
    echo "Instalando el módulo requests..."
    if ! pip3 install requests; then
        echo "Error al instalar el módulo requests. Asegúrate de tener conexión a internet y vuelve a intentarlo."
        exit 1
    fi
fi

# Script y rutas de archivos de servicio
SCRIPT_PATH="/opt/YUMI_SYNC/yumi_sync.py"
SERVICE_PATH="/etc/systemd/system/yumi_sync.service"

# Verificar si el directorio de instalación existe, si no, crearlo
if [ ! -d "/opt/YUMI_SYNC" ]; then
    mkdir -p /opt/YUMI_SYNC
fi

# Crear el script de Python
cat << 'EOF' > "$SCRIPT_PATH"
import os
import time
import requests
import hashlib
import json
from datetime import datetime, timedelta

# El resto del script sigue aquí...
EOF

# Crear el archivo de servicio systemd
cat > "$SERVICE_PATH" <<EOL
[Unit]
Description=Yumi Sync Service

[Service]
ExecStart=/usr/bin/python3 $SCRIPT_PATH
WorkingDirectory=/opt/YUMI_SYNC
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOL

# Recargar systemd para reconocer los cambios
systemctl daemon-reload

# Iniciar el servicio
systemctl start yumi_sync

# Habilitar el servicio para que se inicie en el arranque
systemctl enable yumi_sync

echo "Instalación completada. El servidor está en ejecución."
