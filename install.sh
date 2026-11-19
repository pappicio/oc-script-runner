#!/opt/bin/sh
set -eu

PLUGIN_DIR="${OC_PLUGIN_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)}"
SCRIPTS_DIR="/usr/data/opencreator/scripts"

echo "[Script Runner] Setting plugin permissions..."

find "$PLUGIN_DIR" -type f \( -name "*.sh" -o -name "*.py" \) -exec chmod 755 {} \;
find "$PLUGIN_DIR" -type d -exec chmod 755 {} \;

echo "[Script Runner] Creating scripts directory..."

mkdir -p "$SCRIPTS_DIR"
chmod 755 "$SCRIPTS_DIR"

find "$SCRIPTS_DIR" -type f \( -name "*.sh" -o -name "*.py" \) -exec chmod 755 {} \;

echo "[Script Runner] Installation completed."
