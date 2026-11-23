#!/opt/bin/sh
set -eu

echo "[Script Runner] Uninstall started"

SCRIPTS_DIR="/usr/data/opencreator/scripts"

if [ -d "$SCRIPTS_DIR" ]; then
    echo "[Script Runner] Removing $SCRIPTS_DIR"
    rm -rf "$SCRIPTS_DIR"
fi

echo "[Script Runner] Uninstall completed"
exit 0