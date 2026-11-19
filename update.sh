#!/opt/bin/sh

set -eu

echo "[Script Runner] Update started"

SCRIPTS_DIR="/usr/data/opencreator/scripts"

# Preserve the shared scripts directory and all user files.
if [ ! -d "$SCRIPTS_DIR" ]; then
    mkdir -p "$SCRIPTS_DIR"
    echo "[Script Runner] Created $SCRIPTS_DIR"
else
    echo "[Script Runner] Preserving existing user scripts"
fi

echo "[Script Runner] Update completed"
exit 0
