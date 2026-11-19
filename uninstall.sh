#!/opt/bin/sh

set -eu

echo "[Script Runner] Uninstall started"

# The scripts directory is shared user data.
# Never delete or modify its contents.
SCRIPTS_DIR="/usr/data/opencreator/scripts"

if [ -d "$SCRIPTS_DIR" ]; then
    echo "[Script Runner] Preserving user scripts in $SCRIPTS_DIR"
fi

echo "[Script Runner] Uninstall completed"
exit 0
