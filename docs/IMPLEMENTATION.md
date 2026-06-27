# Implementation Log

**Date:** 2026-06-27  
**Based on:** [docs/reports/report_270626.md](reports/report_270626.md)

This document records every improvement that was implemented from the professional process manager roadmap.

---

## Phase 1 — Stability

### 1. State file moved to user data directory

**File:** `pm/settings.py`

`processes_state.json` now lives in the platform-appropriate user data directory via `platformdirs`:

| Platform | Path |
|----------|------|
| Linux | `~/.local/share/pmflow/processes_state.json` |
| macOS | `~/Library/Application Support/pmflow/processes_state.json` |
| Windows | `%APPDATA%\pmflow\processes_state.json` |

A one-time migration copies the old in-package state file on first launch so existing users lose no data.

**Dependencies added:** `platformdirs>=4.0.0`, `pyyaml>=6.0.0`, `click>=7.1.1,<8.2.0` (Click 8.2+ broke `Argument.make_metavar` compatibility with Typer 0.12.5)

---

### 2. `ProcessRecord` dataclass and typed schema

**File:** `pm/schema.py`

Added `ProcessRecord` dataclass with fields:

| Field | Type | Notes |
|-------|------|-------|
| `pid` | `int` | Process ID |
| `command` | `str` | Shell command |
| `name` | `Optional[str]` | User-assigned name |
| `group` | `str` | Group identifier |
| `relation` | `str` | `parent` or `child` |
| `status` | `str` | Status enum value |
| `exit_code` | `Optional[int]` | Set on process exit |
| `log_file` | `Optional[str]` | Path to log file |
| `autostart` | `bool` | Whether to recreate on `pm recreate` |
| `created_at` | `str` | ISO 8601 UTC timestamp |
| `exited_at` | `Optional[str]` | ISO 8601 UTC timestamp |

`from_dict` uses `.get()` with defaults throughout, so old-format state files load without errors.

---

### 3. Expanded `Status` enum

**File:** `pm/schema.py`

| Value | Meaning |
|-------|---------|
| `running` | Process is alive and active |
| `paused` | Process is suspended (SIGSTOP) |
| `stopped` | Exited with code 0 |
| `crashed` | Exited with non-zero code |
| `unknown` | PID no longer exists, exit not tracked |

`pm ls` now resolves `stopped`/`crashed`/`unknown` correctly instead of showing a generic "doesn't exist".

---

### 4. Graceful stop — `pm stop`

**File:** `pm/commands/stop.py`

New command with SIGTERM → timeout → SIGKILL flow:

```
pm stop <name|pid>              # SIGTERM, wait 10s, then SIGKILL
pm stop <name|pid> --timeout 30 # custom wait period
pm stop <name|pid> --force      # immediate SIGKILL
```

Uses `psutil.wait_procs()` for the timeout. Updates `status`, `exit_code`, and `exited_at` in state. Process entry is **kept** in state after stop (so it can be inspected and restarted).

---

### 5. Process detachment

**File:** `pm/commands/create.py`

Background processes now use:
- Unix: `start_new_session=True` (calls `setsid()` — survives terminal close)
- Windows: `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`

Foreground mode (`--foreground`) skips detachment and blocks until the process exits.

---

## Phase 2 — Observability

### 6. Log file support

**File:** `pm/commands/create.py`

New flag: `--log-file / -l`. When provided, stdout and stderr of the spawned process are redirected to that path (appended). Parent directories are created automatically.

```
pm create "uvicorn app:app" --name api --log-file logs/api.log
```

The log file path is stored in state so `pm info` and `pm logs` can find it.

---

### 7. `pm logs`

**File:** `pm/commands/logs.py`

```
pm logs <name|pid>           # last 20 lines
pm logs <name|pid> -n 100    # last 100 lines
pm logs <name|pid> --follow  # stream new output (Ctrl+C to stop)
```

Looks up the log path from state. Errors with code 1300 if no log file is configured.

---

### 8. `pm info`

**File:** `pm/commands/info.py`

```
pm info <name|pid>
```

Displays a detail panel:

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

Live CPU and memory are queried from psutil at display time.

---

### 9. `pm cleanup`

**File:** `pm/commands/cleanup.py`

Removes all state entries whose PID no longer exists on the system:

```
pm cleanup
```

Useful after a reboot when all stored PIDs are stale.

---

## Phase 3 — Developer Experience

### 10. Command aliases

**File:** `pm/main.py`

| New command | Equivalent |
|-------------|-----------|
| `pm start` | `pm create` |
| `pm status` | `pm ls` |
| `pm stop` | graceful kill (new behavior, not alias) |
| `pm restart` | stop + recreate |

---

### 11. `pm version`

**File:** `pm/main.py`

```
pm version
# pmflow 1.3.0
```

Reads from `importlib.metadata` so it always reflects the installed package version.

---

### 12. `pm restart`

**File:** `pm/commands/stop.py`

```
pm restart <name|pid>
pm restart <name|pid> --timeout 30
```

Gracefully stops the process then starts a new one with the same command, name, group, log file, and autostart flag. New PID is printed.

---

### 13. `pmflow.yaml` and `pm up` / `pm down`

**Files:** `pm/commands/manage.py`, `pmflow.yaml`

Declare all processes in a config file:

```yaml
version: 1
processes:
  api:
    command: uvicorn app:app --host 0.0.0.0 --port 8000
    group: backend
    relation: parent
    log_file: logs/api.log
  worker:
    command: celery -A tasks worker
    group: backend
    relation: child
```

```
pm up          # start all processes from pmflow.yaml
pm down        # stop all processes from pmflow.yaml
pm up --config path/to/other.yaml
```

Parents are started before children so group validation passes. **Dependency added:** `pyyaml>=6.0.0`

---

## Phase 4 — Quality & Automation

### 14. Centralized error codes

**File:** `pm/errors.py`

All error codes and messages are now in one place. The `fmt(code)` helper produces consistent error strings across all commands.

| Code | Meaning |
|------|---------|
| 800 | Child process missing group |
| 801 | Group does not exist |
| 802 | Duplicate parent in group |
| 1000 | Group not found in `pm ls` |
| 1001 | Process not found by name or PID |
| 1100 | `pm kill` missing argument |
| 1200 | `pm kill` too many arguments |
| 1300 | No log file configured |
| 1400 | `pmflow.yaml` not found |
| 1401 | Invalid `pmflow.yaml` |

---

### 15. Test suite

**Directory:** `tests/`

| File | Coverage |
|------|----------|
| `test_schema.py` | `Relation`, `Status`, `ProcessRecord` (to_dict / from_dict / defaults / backward compat) |
| `test_state_manager.py` | All StateManager CRUD methods, persistence round-trip, `get_by_name_or_pid`, group filtering |
| `test_create.py` | Happy path, error codes 800/801/802, `--log-file`, `start` alias |
| `test_kill.py` | By PID, by group, `--all`, unmanaged PID, argument validation |
| `test_ls.py` | Table output, JSON output, group filter, running filter, `status` alias |
| `test_stop.py` | Graceful stop, force stop, by name/pid, crashed status, already-dead process |

Tests use `typer.testing.CliRunner` for CLI integration and `unittest.mock.patch` for subprocess/psutil isolation. The `conftest.py` resets the StateManager singleton between tests and patches `state` in all command modules.

---

### 16. GitHub Actions CI

**File:** `.github/workflows/test.yml`

Test matrix: Python 3.10, 3.11, 3.12, 3.13 × Ubuntu, macOS, Windows (12 jobs). Auto-publish to PyPI on version tags (requires `PYPI_API_TOKEN` secret in the `pypi` environment).

---

### 17. `CHANGELOG.md`

**File:** `CHANGELOG.md`

Added following [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format with entries for 1.3.0, 1.2.16, and 1.0.1.

---

## Files Changed Summary

| File | Change |
|------|--------|
| `pm/errors.py` | **NEW** — centralized error codes |
| `pm/schema.py` | **MODIFIED** — added `Status` enum and `ProcessRecord` dataclass |
| `pm/settings.py` | **MODIFIED** — platformdirs paths, state migration |
| `pm/utils.py` | **MODIFIED** — added `get_by_name_or_pid`, cleaned up, fixed directory creation |
| `pm/commands/create.py` | **MODIFIED** — log-file, process detachment, autostart, timestamps |
| `pm/commands/kill.py` | **MODIFIED** — refactored helpers, uses `errors.fmt()` |
| `pm/commands/ls.py` | **MODIFIED** — expanded status resolution, color-coded status column |
| `pm/commands/stop.py` | **NEW** — graceful `stop` and `restart` commands |
| `pm/commands/info.py` | **NEW** — `pm info` detail view |
| `pm/commands/logs.py` | **NEW** — `pm logs` tail command |
| `pm/commands/cleanup.py` | **NEW** — `pm cleanup` stale entry removal |
| `pm/commands/manage.py` | **NEW** — `pm up` / `pm down` from `pmflow.yaml` |
| `pm/main.py` | **MODIFIED** — all new commands registered, aliases, `pm version`, removed `greet` |
| `pyproject.toml` | **MODIFIED** — version 1.3.0, new deps, pytest config |
| `tests/__init__.py` | **NEW** |
| `tests/conftest.py` | **NEW** — singleton reset + state patcher fixture |
| `tests/test_schema.py` | **NEW** |
| `tests/test_state_manager.py` | **NEW** |
| `tests/test_create.py` | **NEW** |
| `tests/test_kill.py` | **NEW** |
| `tests/test_ls.py` | **NEW** |
| `tests/test_stop.py` | **NEW** |
| `.github/workflows/test.yml` | **NEW** — CI + PyPI publish workflow |
| `CHANGELOG.md` | **NEW** |
| `pmflow.yaml` | **NEW** — example config |
| `docs/reports/report_270626.md` | **MODIFIED** — added link to this file |
