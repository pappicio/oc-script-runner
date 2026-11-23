#!/opt/bin/sh
set -eu

SCRIPTS_DIR="/usr/data/opencreator/scripts"

echo "[Script Runner] Removing scripts directory..."

if [ -d "$SCRIPTS_DIR" ]; then
    rm -rf "$SCRIPTS_DIR"
fi

echo "[Script Runner] Installation completed."

exit 0


