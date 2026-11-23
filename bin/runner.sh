#!/opt/bin/sh

SCRIPTS_DIR="/usr/data/opencreator/scripts"

if [ -d "$SCRIPTS_DIR" ]; then
    find "$SCRIPTS_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
fi

exit 0