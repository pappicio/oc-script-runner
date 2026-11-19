#
# Script Runner

Script Runner is an OpenCreator plugin that automatically executes user scripts at startup in both SoC and Tunneled modes.

## Directory structure

Scripts are stored in:

```text
/usr/data/opencreator/scripts/
+-- both/       # Executed in both modes
+-- soc/        # Executed only in SoC mode
+-- tunneled/   # Executed only in Tunneled mode
```

All three directories are created automatically when the runner starts.

## Execution order

The runner starts scripts in this order:

1. All `*.sh` files in `both/`, alphabetically.
2. All `*.py` files in `both/`, alphabetically.
3. All `*.sh` files in the active mode directory, alphabetically.
4. All `*.py` files in the active mode directory, alphabetically.

Scripts are started in the background. The runner starts the next group without waiting for scripts in the previous group to finish.

Each script runs with its working directory set to its own folder.

- Shell scripts are executed using `sh`.
- Python scripts are executed using the selected Python interpreter.

The preferred Python interpreter is:

```text
/usr/data/python-hf/bin/python3
```

If it is unavailable or not executable, the runner tries `python3` and then `python` from the system `PATH`.

## Operating mode detection

The runner uses `OC_TUNNELED` provided by OpenCreator when the variable is present:

- `OC_TUNNELED=1`: Tunneled mode.
- Any other value, including an empty value: SoC mode.

If `OC_TUNNELED` is not defined, the runner falls back to checking whether this file is executable:

```text
/usr/data/opencreator/tunneled/tunneled.sh
```

## Environment variables

Scripts inherit the environment provided by OpenCreator, including variables such as:

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

In Tunneled mode, the runner uses the Moonraker URL supplied by OpenCreator. If unavailable, it attempts discovery through `oc-plugin moonraker --find`, then falls back to the cached URL.

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

Place scripts in the appropriate directory.

To restart the runner after adding or modifying scripts:

```sh
oc-plugin restart script-runner runner
```

To view the OpenCreator service log:

```sh
oc-plugin logs script-runner runner
```

## Logging

The runner uses exactly four log files, all stored directly in `/tmp`:

```text
/tmp/oc-script-runner.log
/tmp/oc-script-runner-both.log
/tmp/oc-script-runner-soc.log
/tmp/oc-script-runner-tunneled.log
```

| Log file | Contents |
|---|---|
| `oc-script-runner.log` | Startup information, detected mode, Moonraker configuration and process status |
| `oc-script-runner-both.log` | Output from scripts in `both/` |
| `oc-script-runner-soc.log` | Output from scripts in `soc/` |
| `oc-script-runner-tunneled.log` | Output from scripts in `tunneled/` |

Each mode-specific log includes script output, start notifications and exit status.

All four log files are overwritten whenever the runner starts. Since they are stored in `/tmp`, they reside in RAM and are not intended for persistent logging.

## Process management

The runner remains active as an OpenCreator service after all startup scripts have completed.

When the service is stopped or the plugin is removed, OpenCreator terminates the runner's managed process group, including child processes that remain in that group.

Processes that deliberately detach themselves from the managed process group (for example, by using `setsid`) may survive the service stop.

## Notes

- Scripts need to be readable by the user running the plugin. They do not need executable permissions because they are launched through `sh` or Python.
- The script directories must remain accessible to the plugin process.
- If `OC_TUNNELED` is not defined, the fallback mode detection requires `/usr/data/opencreator/tunneled/tunneled.sh` to be executable.
- Use LF line endings for shell scripts. CRLF line endings may cause execution errors.
