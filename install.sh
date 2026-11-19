#!/opt/bin/sh
set -eu

SCRIPTS_DIR="/usr/data/opencreator/scripts"

mkdir -p "$SCRIPTS_DIR"
chmod 755 "$SCRIPTS_DIR"

find "$SCRIPTS_DIR" -type f \( -name "*.sh" -o -name "*.py" \) -exec chmod 755 {} \;

echo "[Script Runner] Scripts directory ready: $SCRIPTS_DIR"
