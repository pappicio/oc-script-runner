
#!/opt/bin/sh

BASE="/usr/data/opencreator/scripts"
LOG="/tmp/oc-script-runner.log"

PY="/usr/data/python-hf/bin/python3"
PIDS=""

export PYTHONUNBUFFERED=1
export LC_ALL=C

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"
}


sleep 5

# --------------------------------------------------
# Initialize log
# --------------------------------------------------

: > "$LOG"

# --------------------------------------------------
# Detect operating mode
# --------------------------------------------------

if [ "${OC_TUNNELED+x}" = "x" ]; then
    if [ "$OC_TUNNELED" = "1" ]; then
        MODE="tunneled"
    else
        MODE="soc"
    fi
elif [ -x /usr/data/opencreator/tunneled/tunneled.sh ]; then
    MODE="tunneled"
else
    MODE="soc"
fi

export OC_RUNNER_MODE="$MODE"

# --------------------------------------------------
# Select Python interpreter
# --------------------------------------------------

if [ ! -x "$PY" ]; then
    PY="$(command -v python3 2>/dev/null)"
fi

if [ ! -x "$PY" ]; then
    PY="$(command -v python 2>/dev/null)"
fi

# --------------------------------------------------
# Resolve Moonraker URL
# --------------------------------------------------

if [ -z "$OC_MOONRAKER_URL" ]; then
    if [ "$MODE" = "soc" ]; then
        OC_MOONRAKER_URL="http://127.0.0.1:7125"
    else
        OC_MOONRAKER_URL="$(oc-plugin moonraker --find 2>/dev/null | tail -n 1)"

        if [ -z "$OC_MOONRAKER_URL" ]; then
            CACHE="/usr/data/opencreator/plugins/.moonraker-url"
            [ -r "$CACHE" ] && OC_MOONRAKER_URL="$(head -n 1 "$CACHE")"
        fi
    fi
fi

export OC_MOONRAKER_URL

# --------------------------------------------------
# Extract Moonraker hostname/IP and port
# --------------------------------------------------

OC_MOONRAKER_IP=""
OC_MOONRAKER_PORT=""

if [ -n "$PY" ]; then
    set -- $("$PY" -c '
import sys
from urllib.parse import urlparse

try:
    u = urlparse(sys.argv[1])
    print(u.hostname or "")
    print(u.port or (443 if u.scheme == "https" else 80))
except Exception:
    print("")
    print("")
' "$OC_MOONRAKER_URL" 2>/dev/null)

    OC_MOONRAKER_IP="${1:-}"
    OC_MOONRAKER_PORT="${2:-}"
fi

export OC_MOONRAKER_IP OC_MOONRAKER_PORT

# --------------------------------------------------
# Run scripts
# --------------------------------------------------

run_scripts() {
    DIR="$1"

    [ -d "$DIR" ] || return 0

    # Start shell scripts first.
    for SCRIPT in "$DIR"/*.sh; do
        [ -f "$SCRIPT" ] || continue

        (
            cd "$DIR" || exit 1

            echo
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] START $SCRIPT"

            sh "$SCRIPT"
            RC=$?

            if [ "$RC" -eq 0 ]; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] OK $SCRIPT"
            else
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR ($RC) $SCRIPT"
            fi

            exit "$RC"
        ) >> "$LOG" 2>&1 &

        PID=$!
        PIDS="$PIDS $PID"
        log "Started $SCRIPT PID=$PID"
    done

    # Start Python scripts after shell scripts.
    for SCRIPT in "$DIR"/*.py; do
        [ -f "$SCRIPT" ] || continue

        (
            cd "$DIR" || exit 1

            echo
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] START $SCRIPT"

            if [ -n "$PY" ]; then
                "$PY" "$SCRIPT"
                RC=$?
            else
                echo "ERROR: Python interpreter not found"
                RC=127
            fi

            if [ "$RC" -eq 0 ]; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] OK $SCRIPT"
            else
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR ($RC) $SCRIPT"
            fi

            exit "$RC"
        ) >> "$LOG" 2>&1 &

        PID=$!
        PIDS="$PIDS $PID"
        log "Started $SCRIPT PID=$PID"
    done
}

# --------------------------------------------------
# Initialize and start
# --------------------------------------------------

mkdir -p "$BASE"

log "=========================================="
log "Script Runner starting"
log "Mode: $MODE"
log "Moonraker URL: $OC_MOONRAKER_URL"
log "Moonraker IP: $OC_MOONRAKER_IP"
log "Moonraker port: $OC_MOONRAKER_PORT"
log "Python: ${PY:-NOT FOUND}"
log "Scripts directory: $BASE"
log "=========================================="

run_scripts "$BASE"

log "All scripts launched. Waiting for completion."

# Wait for all directly started scripts.
for PID in $PIDS; do
    wait "$PID"
    RC=$?
    log "Process PID=$PID completed with exit code $RC"
done

log "All scripts completed. Runner entering idle state."

# Keep the OpenCreator service alive.
while true; do
    sleep 3600
done
