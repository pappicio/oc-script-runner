
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import fcntl
import glob
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime
from urllib.parse import urlparse

BASE = "/usr/data/opencreator/scripts"

LOG = "/tmp/oc-script-runner.log"
LOCK = "/tmp/oc-script-runner.lock"

POLL_INTERVAL = 0.5
SHUTDOWN_TIMEOUT = 8

PERSISTENT_MARKER = "# OC_RUNNER: persistent"
MARKER_LINES = 20

RESTART_INITIAL_DELAY = 3
RESTART_MAX_DELAY = 60
RESTART_RESET_AFTER = 60

STOP = False
CHILDREN = {}


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(message):
    line = "[{}] {}".format(timestamp(), message)

    try:
        with open(LOG, "a") as stream:
            stream.write(line + "\n")
            stream.flush()
    except Exception:
        print(line, file=sys.stderr, flush=True)


def stop_handler(signum, frame):
    global STOP

    if not STOP:
        STOP = True
        log("Received signal {}. Shutdown requested.".format(signum))


def acquire_lock():
    stream = open(LOCK, "a")

    try:
        fcntl.flock(
            stream.fileno(),
            fcntl.LOCK_EX | fcntl.LOCK_NB
        )
    except BlockingIOError:
        stream.close()
        print("Script Runner is already running.", file=sys.stderr)
        return None

    return stream


def inspect_persistence(path):
    try:
        with open(path, "r", errors="replace") as stream:
            for number, line in enumerate(stream, 1):
                if number > MARKER_LINES:
                    break

                marker = line.strip().lower()
                marker = marker.replace(" ", "").replace("\t", "")

                if marker == "#oc_runner:persistent":
                    return True, number

    except (OSError, UnicodeError) as exc:
        log("Unable to inspect {}: {}".format(
            os.path.basename(path), exc
        ))

    return False, None



def initialize_environment():
    env = os.environ.copy()

    env["PYTHONUNBUFFERED"] = "1"
    env["LC_ALL"] = "C"

    # Detect operating mode.
    if "OC_TUNNELED" in env:
        mode = (
            "tunneled"
            if env["OC_TUNNELED"] == "1"
            else "soc"
        )
    elif os.access(
        "/usr/data/opencreator/tunneled/tunneled.sh",
        os.X_OK
    ):
        mode = "tunneled"
    else:
        mode = "soc"

    env["OC_RUNNER_MODE"] = mode

    # Resolve Moonraker URL.
    moonraker_url = env.get("OC_MOONRAKER_URL", "")

    if not moonraker_url:
        if mode == "soc":
            moonraker_url = "http://127.0.0.1:7125"

        else:
            try:
                result = subprocess.run(
                    ["oc-plugin", "moonraker", "--find"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    universal_newlines=True,
                    timeout=10,
                    env=env
                )

                lines = [
                    line.strip()
                    for line in result.stdout.splitlines()
                    if line.strip()
                ]

                if lines:
                    moonraker_url = lines[-1]

            except Exception as exc:
                log("Moonraker discovery failed: {}".format(exc))

            if not moonraker_url:
                cache = (
                    "/usr/data/opencreator/plugins/"
                    ".moonraker-url"
                )

                try:
                    with open(cache, "r") as stream:
                        moonraker_url = stream.readline().strip()
                except OSError:
                    pass

    env["OC_MOONRAKER_URL"] = moonraker_url

    # Resolve Moonraker IP and port.
    try:
        parsed = urlparse(moonraker_url)

        host = parsed.hostname or ""
        port = parsed.port or (
            443 if parsed.scheme == "https" else 80
        )

    except Exception:
        host = ""
        port = ""

    env["OC_MOONRAKER_IP"] = host
    env["OC_MOONRAKER_PORT"] = str(port) if port else ""

    return env, mode


def schedule_restart(name, child, attempt, now=None):
    if STOP or not child["persistent"]:
        return

    if now is None:
        now = time.monotonic()

    delay = min(
        RESTART_INITIAL_DELAY * (2 ** attempt),
        RESTART_MAX_DELAY
    )

    child["attempt"] = attempt + 1
    child["restart_at"] = now + delay

    log(
        "Scheduled restart for {} in {} seconds.".format(
            name, delay
        )
    )


def start_script(path, env, attempt=0, persistent=None):
    name = os.path.basename(path)

    if persistent is None:
        persistent, marker_line = inspect_persistence(path)

        if persistent:
            log(
                "Classification: {} = PERSISTENT "
                "(marker found at line {}).".format(
                    name, marker_line
                )
            )
        else:
            log(
                "Classification: {} = ONE-SHOT "
                "(marker not found in first {} lines).".format(
                    name, MARKER_LINES
                )
            )

    if path.endswith(".sh"):
        shell = shutil.which("sh") or "/opt/bin/sh"
        command = [shell, path]
    else:
        command = [sys.executable, path]

    child = {
        "path": path,
        "process": None,
        "pgid": None,
        "persistent": persistent,
        "attempt": attempt,
        "restart_at": None,
        "started_at": None
    }

    CHILDREN[name] = child

    try:
        with open(LOG, "a") as output:
            process = subprocess.Popen(
                command,
                cwd=BASE,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                close_fds=True,
                start_new_session=True
            )

    except Exception as exc:
        log("ERROR starting {}: {}".format(name, exc))
        schedule_restart(name, child, attempt)
        return None

    child["process"] = process
    child["pgid"] = process.pid
    child["started_at"] = time.monotonic()

    log(
        "Started {} PID={} [{}].".format(
            name,
            process.pid,
            "PERSISTENT" if persistent else "ONE-SHOT"
        )
    )

    return process


def launch_scripts(env):
    os.makedirs(BASE, exist_ok=True)

    shell_scripts = sorted(
        path
        for path in glob.glob(os.path.join(BASE, "*.sh"))
        if os.path.isfile(path)
    )

    python_scripts = sorted(
        path
        for path in glob.glob(os.path.join(BASE, "*.py"))
        if os.path.isfile(path)
    )

    # Start all shell scripts first.
    for path in shell_scripts:
        if STOP:
            return

        start_script(path, env)

    # Then start all Python scripts.
    for path in python_scripts:
        if STOP:
            return

        start_script(path, env)


def process_group_exists(pgid):
    if not pgid:
        return False

    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def terminate_group(pgid, timeout=SHUTDOWN_TIMEOUT):
    if not process_group_exists(pgid):
        return

    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except Exception as exc:
        log("SIGTERM failed for process group {}: {}".format(
            pgid, exc
        ))
        return

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if not process_group_exists(pgid):
            return

        time.sleep(0.2)

    if process_group_exists(pgid):
        log("Force stopping process group {}.".format(pgid))

        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except Exception as exc:
            log("SIGKILL failed for process group {}: {}".format(
                pgid, exc
            ))


def monitor_children(env):
    while not STOP:
        now = time.monotonic()

        for name, child in list(CHILDREN.items()):
            if STOP:
                break

            process = child["process"]

            if process is not None:
                return_code = process.poll()

                if return_code is None:
                    continue

                runtime = now - child["started_at"]

                child["process"] = None

                if child["persistent"]:
                    log(
                        "Persistent service {} PID={} exited "
                        "with code {} after {:.1f}s.".format(
                            name,
                            process.pid,
                            return_code,
                            runtime
                        )
                    )
                else:
                    status = (
                        "completed"
                        if return_code == 0
                        else "failed"
                    )

                    log(
                        "One-shot {} PID={} {} with code {}.".format(
                            name,
                            process.pid,
                            status,
                            return_code
                        )
                    )

                # Clean up descendants left behind by the script.
                terminate_group(child["pgid"], timeout=2)

                if child["persistent"]:
                    next_attempt = (
                        0
                        if runtime >= RESTART_RESET_AFTER
                        else child["attempt"]
                    )

                    schedule_restart(
                        name,
                        child,
                        next_attempt,
                        now
                    )

            elif (
                child["restart_at"] is not None
                and now >= child["restart_at"]
            ):
                if STOP:
                    break

                log("Restarting persistent service {}.".format(name))

                start_script(
                    child["path"],
                    env,
                    child["attempt"],
                    child["persistent"]
                )

        time.sleep(POLL_INTERVAL)


def shutdown():
    log("Stopping managed child processes.")

    groups = set()

    # Send SIGTERM to every managed process group.
    for name, child in list(CHILDREN.items()):
        pgid = child["pgid"]

        if pgid and process_group_exists(pgid):
            groups.add(pgid)

            log(
                "Stopping {} process group {}.".format(
                    name, pgid
                )
            )

            try:
                os.killpg(pgid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except Exception as exc:
                log("SIGTERM failed for {}: {}".format(name, exc))

    # Use one shared shutdown deadline.
    deadline = time.monotonic() + SHUTDOWN_TIMEOUT

    while groups and time.monotonic() < deadline:
        groups = {
            pgid for pgid in groups
            if process_group_exists(pgid)
        }

        if groups:
            time.sleep(0.2)

    # Force remaining groups to stop.
    for pgid in groups:
        log("Force stopping process group {}.".format(pgid))

        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except Exception as exc:
            log("SIGKILL failed for group {}: {}".format(
                pgid, exc
            ))

    # Reap managed processes.
    for child in CHILDREN.values():
        process = child["process"]

        if process is not None:
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            except Exception:
                pass

    log("Child process shutdown completed.")


def main():
    global STOP

    lock = acquire_lock()

    if lock is None:
        return 0

    signal.signal(signal.SIGTERM, stop_handler)
    signal.signal(signal.SIGINT, stop_handler)

    try:
        # Preserve original startup delay.
        ##### time.sleep(3)

        if STOP:
            return 0

        # Only the lock owner may reset the log.
        with open(LOG, "w"):
            pass

        env, mode = initialize_environment()

        log("==========================================")
        log("Script Runner starting")
        log("Mode: {}".format(mode))
        log("Moonraker URL: {}".format(
            env.get("OC_MOONRAKER_URL", "")
        ))
        log("Moonraker IP: {}".format(
            env.get("OC_MOONRAKER_IP", "")
        ))
        log("Moonraker port: {}".format(
            env.get("OC_MOONRAKER_PORT", "")
        ))
        log("Python: {}".format(sys.executable))
        log("Scripts directory: {}".format(BASE))
        log("Persistent marker: {}".format(PERSISTENT_MARKER))
        log("Marker search range: first {} lines".format(
            MARKER_LINES
        ))
        log("==========================================")

        launch_scripts(env)

        log("All scripts launched. Monitoring processes.")

        monitor_children(env)

    except Exception as exc:
        log("FATAL: {}".format(exc))
        return 1

    finally:
        STOP = True
        shutdown()
        log("Script Runner stopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
