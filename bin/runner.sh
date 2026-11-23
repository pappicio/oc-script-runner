#!/opt/bin/sh

SCRIPTS_DIR="/usr/data/opencreator/scripts"

if [ -d "$SCRIPTS_DIR" ]; then
    rm -rf "$SCRIPTS_DIR"
fi

exit 0
