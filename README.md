
# Script Runner

Script Runner is an OpenCreator plugin that automatically executes user scripts at startup in both SoC and Tunneled modes.

## Directory structure

All scripts are stored in a single directory:

```text
/usr/data/opencreator/scripts/
├── backup.sh
├── monitor.py
├── fan-control.py
└── my-script.sh
```

The directory is created automatically when the runner starts.

## Execution

The runner executes scripts in the following order:

1. All `*.sh` files, alphabetically.
2. All `*.py` files, alphabetically.

All scripts are started in the background. The runner does not wait for one script to finish before starting the next.

Each script runs with its working directory set to:

```text
/usr/data/opencreator/scripts/
```

- Shell scripts are executed using `sh`.
- Python scripts are executed using the selected Python interpreter.

The preferred Python interpreter is:

```text
/usr/data/python-hf/bin/python3
```

If it is unavailable or not executable, the runner tries `python3` and then `python` from the system `PATH`.

## Operating mode

Scripts can detect the current operating mode using environment variables provided by the runner.

| Variable | Description |
|---|---|
| `OC_TUNNELED` | `1` in Tunneled mode; otherwise SoC mode |
| `OC_RUNNER_MODE` | `tunneled` or `soc` |

Example in Python:

```python
import os

if os.environ.get("OC_TUNNELED") == "1":
    print("Running in Tunneled mode")
else:
    print("Running in SoC mode")
```

Example in Shell:

```sh
if [ "${OC_TUNNELED:-0}" = "1" ]; then
    echo "Running in Tunneled mode"
else
    echo "Running in SoC mode"
fi
```

## Environment variables

Scripts inherit the environment provided by OpenCreator, including:

- `OC_TUNNELED`
- `OC_MOONRAKER_URL`
- `OC_PLUGIN_DATA`

The runner additionally exports:

| Variable | Description |
|---|---|
| `OC_RUNNER_MODE` | Active mode: `soc` or `tunneled` |
| `OC_MOONRAKER_URL` | Moonraker server URL |
| `OC_MOONRAKER_IP` | Moonraker hostname or IP address |
| `OC_MOONRAKER_PORT` | Moonraker port |
| `PYTHONUNBUFFERED` | Set to `1` for unbuffered Python output |

In Tunneled mode, the runner uses the Moonraker URL provided by OpenCreator. If unavailable, it attempts discovery through `oc-plugin moonraker --find`, then falls back to the cached URL.

In SoC mode, the default Moonraker URL is:

```text
http://127.0.0.1:7125
```

## Installation

Install the plugin using:

```sh
oc-plugin install /usr/data/oc-script-runner
```

## Usage

Place your scripts in:

```text
/usr/data/opencreator/scripts/
```

To restart the runner after adding or modifying scripts:

```sh
oc-plugin restart script-runner runner
```

To view the OpenCreator service log:

```sh
oc-plugin logs script-runner runner
```

## Logging

The runner uses a single log file:

```text
/tmp/oc-script-runner.log
```

It contains:

- Startup information and detected operating mode.
- Moonraker configuration.
- Python interpreter selection.
- Script start notifications.
- Standard output and standard error from all scripts.
- Script exit status.

The log is overwritten whenever the runner starts.

Since it is stored in `/tmp`, it resides in RAM and is not intended for persistent logging.

## Process management

The runner remains active as an OpenCreator service after all startup scripts have completed.

When the service is stopped or the plugin is removed, OpenCreator terminates the runner's managed process group, including child processes that remain in that group.

Processes that deliberately detach themselves from the managed process group (for example, by using `setsid`) may survive the service stop.

## Notes

- Scripts must be readable by the user running the plugin.
- Scripts do not need executable permissions because they are launched through `sh` or Python.
- Use LF line endings for shell scripts. CRLF line endings may cause execution errors.
