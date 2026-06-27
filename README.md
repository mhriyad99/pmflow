# PMFlow

A lightweight CLI process manager. Spawn, monitor, and control long-running subprocesses from the terminal — with persistent state, process groups, log capture, and graceful lifecycle management.

```
pip install pmflow
```

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [State Storage](#state-storage)
- [Commands](#commands)
  - [create / start](#create--start)
  - [ls / status](#ls--status)
  - [info](#info)
  - [logs](#logs)
  - [stop](#stop)
  - [restart](#restart)
  - [kill](#kill)
  - [pause / respawn](#pause--respawn)
  - [recreate](#recreate)
  - [cleanup](#cleanup)
  - [up / down](#up--down)
  - [version](#version)
- [Config File (pmflow.yaml)](#config-file-pmflowyaml)
- [Process Groups](#process-groups)
- [Error Codes](#error-codes)
- [Windows Notes](#windows-notes)

---

## Installation

```
pip install pmflow
```

**Windows:** After installing, make sure the Python `Scripts` directory is on your PATH. Find it with:

```
pip show pmflow
```

The location will be something like `C:\Users\<you>\AppData\Local\Programs\Python\Python3x\Scripts`. Add that to your system PATH if `pm` is not found after install.

---

## Quick Start

```
# Start a process
pm create "python app.py" --name api

# See what's running
pm ls

# See details for one process
pm info api

# Follow its logs
pm logs api --follow

# Gracefully stop it
pm stop api

# Start everything from a config file
pm up
```

---

## State Storage

PMFlow stores process metadata in a JSON file in your user data directory:

| Platform | Location |
|----------|----------|
| Linux    | `~/.local/share/pmflow/processes_state.json` |
| macOS    | `~/Library/Application Support/pmflow/processes_state.json` |
| Windows  | `%APPDATA%\pmflow\processes_state.json` |

State persists across terminal sessions and survives `pip install --upgrade pmflow`.

---

## Commands

### `create` / `start`

Start a new subprocess. `start` is an alias for `create`.

```
pm create "<command>" [OPTIONS]
pm start  "<command>" [OPTIONS]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--name` | `-n` | None | Human-readable name for the process |
| `--group` | `-g` | auto | Group name (auto-generated for parent processes) |
| `--relation` | `-r` | `parent` | `parent` or `child` (see [Process Groups](#process-groups)) |
| `--foreground` | `-f` | off | Block until the process exits (useful in `.service` files) |
| `--log-file` | `-l` | None | File path to capture stdout and stderr |
| `--no-autostart` | | off | Exclude from `pm recreate` bulk-restart |
| `--verbose` | `-v` | off | Print the log file path after starting |

**Examples:**

```
# Basic
pm create "python server.py"

# Named process with log capture
pm create "uvicorn app:app --port 8000" --name api --log-file logs/api.log

# Child process in an existing group
pm create "celery -A tasks worker" --name worker --group backend --relation child

# Run in foreground (blocks)
pm create "pytest tests/" --foreground
```

**Notes:**
- Background processes are fully detached — they survive terminal close.
- A child process requires `--group` pointing to an existing parent group.
- Each group may have only one parent.

---

### `ls` / `status`

List all managed processes. `status` is an alias for `ls`.

```
pm ls [OPTIONS]
pm status [OPTIONS]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--json` | `-j` | off | Output raw JSON instead of a table |
| `--group` | `-g` | None | Filter by group name |
| `--running` | `-r` | off | Show only running processes |

**Examples:**

```
pm ls
pm ls --running
pm ls --group backend
pm ls --json
pm ls --json --group backend
```

**Status values:**

| Status | Meaning |
|--------|---------|
| `running` | Process is alive |
| `paused` | Suspended with SIGSTOP |
| `stopped` | Exited cleanly (code 0) |
| `crashed` | Exited with non-zero code |
| `unknown` | PID gone, exit not tracked |

---

### `info`

Show detailed information about a single process, looked up by name or PID.

```
pm info <name|pid>
```

**Example output:**

```
Name          api
PID           12345
Status        running
Command       uvicorn app:app --host 0.0.0.0 --port 8000
Group         backend
Relation      parent
Autostart     True
Log file      logs/api.log
Created at    2026-06-27T09:14:32+00:00
Exited at     —
Exit code     —
Uptime        4h 22m
CPU           1.2%
Memory (RSS)  128.0 MB
```

---

### `logs`

Print the log file for a process. The process must have been started with `--log-file`.

```
pm logs <name|pid> [OPTIONS]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--lines` | `-n` | 20 | Number of lines to show |
| `--follow` | `-f` | off | Stream new output continuously (Ctrl+C to stop) |

**Examples:**

```
pm logs api
pm logs api --lines 100
pm logs api --follow
pm logs 12345 -n 50 -f
```

---

### `stop`

Gracefully stop a process. Sends SIGTERM, waits for it to exit, then sends SIGKILL if it doesn't.

The process entry is **kept in state** after stopping (use `pm kill` to also remove it, or `pm restart` to bring it back up).

```
pm stop <name|pid> [OPTIONS]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--timeout` | `-t` | 10 | Seconds to wait before SIGKILL |
| `--force` | `-F` | off | Skip SIGTERM and send SIGKILL immediately |

**Examples:**

```
pm stop api
pm stop api --timeout 30
pm stop api --force
pm stop 12345
```

After stopping, `pm ls` will show status `stopped` (clean exit) or `crashed` (non-zero exit code).

---

### `restart`

Stop a process and immediately restart it with the same command, name, group, and log file.

```
pm restart <name|pid> [OPTIONS]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--timeout` | `-t` | 10 | Seconds before SIGKILL during the stop phase |

**Example:**

```
pm restart api
pm restart api --timeout 30
```

---

### `kill`

Immediately terminate a process and **remove it from state**. For graceful shutdown, use `pm stop` instead.

```
pm kill <pid>
pm kill --group <name>
pm kill --all
```

| Option | Short | Description |
|--------|-------|-------------|
| `--group` | `-g` | Kill all processes in a group |
| `--child` | `-c` | (With `--group`) kill only child processes, spare the parent |
| `--all` | `-a` | Kill and remove every managed process |

**Examples:**

```
pm kill 12345
pm kill --group backend
pm kill --group backend --child
pm kill --all
```

Killing a parent process automatically kills all its children.

---

### `pause` / `respawn`

Suspend a process without terminating it, then resume it later.

```
pm pause <pid>     # send SIGSTOP to the process and its children
pm respawn         # resume all paused processes (SIGCONT)
```

**Note:** SIGSTOP/SIGCONT are Unix signals and are not available on Windows.

---

### `recreate`

Restart all managed processes from their stored commands. Useful after a reboot when all PIDs are stale.

```
pm recreate
```

Spawns a new subprocess for each entry in state and updates the PIDs. Use `pm cleanup` first to remove any entries you don't want restarted.

---

### `cleanup`

Remove all state entries whose process no longer exists. Useful after a reboot.

```
pm cleanup
```

---

### `up` / `down`

Start or stop all processes defined in `pmflow.yaml`. See [Config File](#config-file-pmflowyaml).

```
pm up                        # start all processes from pmflow.yaml
pm down                      # stop all processes from pmflow.yaml
pm up --config path/to.yaml  # use a different config file
pm down --config path/to.yaml
```

---

### `version`

Print the installed version of pmflow.

```
pm version
# pmflow 1.3.0
```

---

## Config File (pmflow.yaml)

Define all your processes in a `pmflow.yaml` file in your project directory, then use `pm up` / `pm down` to manage them all at once — similar to `docker-compose`.

```yaml
version: 1

processes:
  api:
    command: uvicorn app:app --host 0.0.0.0 --port 8000
    group: backend
    relation: parent
    log_file: logs/api.log
    autostart: true

  worker:
    command: celery -A tasks worker --loglevel=info
    group: backend
    relation: child
    log_file: logs/worker.log
    autostart: true

  scheduler:
    command: celery -A tasks beat
    group: backend
    relation: child
    log_file: logs/scheduler.log
    autostart: false
```

**Fields per process:**

| Field | Required | Description |
|-------|----------|-------------|
| `command` | yes | Shell command to run |
| `group` | no | Group name (auto-generated if omitted for parent) |
| `relation` | no | `parent` (default) or `child` |
| `log_file` | no | Path to redirect stdout/stderr |
| `autostart` | no | Include in `pm recreate` (default: `true`) |

`pm up` starts parents before children so group validation passes.

---

## Process Groups

Groups let you manage related processes together.

- Each group has exactly **one parent** process.
- A group can have **many child** processes.
- Killing or stopping a parent cascades to all its children.

```
# Start a parent (creates group "backend" automatically)
pm create "nginx" --name proxy --group backend

# Add children to the same group
pm create "python worker.py" --name worker --group backend --relation child
pm create "python beat.py"   --name beat   --group backend --relation child

# Inspect the group
pm ls --group backend

# Stop the whole group
pm kill --group backend
```

---

## Error Codes

| Code | Trigger | Meaning |
|------|---------|---------|
| 800 | `pm create` | Child process created without `--group` |
| 801 | `pm create` | `--group` does not match any existing parent group |
| 802 | `pm create` | A parent already exists for that group |
| 1000 | `pm ls` | `--group` filter matched no processes |
| 1001 | `pm stop`, `pm info`, `pm logs` | Name or PID not found in state |
| 1100 | `pm kill` | No argument provided (need PID, `--group`, or `--all`) |
| 1200 | `pm kill` | More than one of PID / `--group` / `--all` given |
| 1300 | `pm logs` | Process has no log file configured |
| 1400 | `pm up`, `pm down` | `pmflow.yaml` not found |
| 1401 | `pm up`, `pm down` | `pmflow.yaml` is not valid YAML |

---

## Windows Notes

- `pm pause` / `pm respawn` use SIGSTOP/SIGCONT which are **not available on Windows**. These commands will fail on Windows.
- `pm stop --force` uses `TerminateProcess` on Windows, which is always immediate regardless of the `--timeout` setting.
- Background processes use `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` flags to survive terminal close.
- Make sure the Python `Scripts` directory is on your PATH after installation (see [Installation](#installation)).
