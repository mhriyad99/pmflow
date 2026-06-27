# Architecture Overview

## What PMFlow Does

PMFlow wraps `subprocess.Popen` with a persistent JSON state file and a Typer CLI. Every process PMFlow spawns gets a record in the state file (PID, command, name, group, relation, status, log path, timestamps). Subsequent commands (`ls`, `stop`, `info`, etc.) read that record to act on the process via `psutil`.

---

## Repository Layout

```
pmflow/
├── pm/                         # Installable package
│   ├── __init__.py
│   ├── main.py                 # Typer app — registers all commands
│   ├── schema.py               # Relation, Status enums; ProcessRecord dataclass
│   ├── settings.py             # Runtime paths (platformdirs) + StateManager singleton
│   ├── utils.py                # StateManager class
│   ├── errors.py               # Error code registry and fmt() helper
│   └── commands/
│       ├── __init__.py
│       ├── create.py           # create, start, recreate, respawn
│       ├── kill.py             # kill, pause
│       ├── ls.py               # ls, status
│       ├── stop.py             # stop, restart
│       ├── info.py             # info
│       ├── logs.py             # logs
│       ├── cleanup.py          # cleanup
│       └── manage.py           # up, down (pmflow.yaml)
├── tests/
│   ├── conftest.py             # Shared fixtures
│   ├── test_schema.py
│   ├── test_state_manager.py
│   ├── test_create.py
│   ├── test_kill.py
│   ├── test_ls.py
│   └── test_stop.py
├── docs/
│   ├── index.md                # Docs index (you are here → one level up)
│   ├── dev/                    # Developer documentation
│   └── reports/                # Design reports
├── .github/workflows/test.yml  # CI + PyPI publish
├── pyproject.toml
├── pmflow.yaml                 # Example config (also used for pm up/down)
├── CHANGELOG.md
└── README.md                   # End-user manual
```

---

## Module Responsibilities

### `pm/main.py`

The single entry point. Instantiates a `typer.Typer()` app and registers every command function (some registered twice for aliasing, e.g. `create` + `start`). No business logic lives here.

### `pm/schema.py`

Pure data definitions — no I/O, no imports from the rest of `pm`:

- `Relation` (`str` enum): `parent` | `child`
- `Status` (`str` enum): `running` | `paused` | `stopped` | `crashed` | `unknown`
- `ProcessRecord` (dataclass): the canonical shape of one state entry. `from_dict` is backward-compatible — missing keys get defaults so old state files load cleanly.

### `pm/errors.py`

`ERROR_CODES: Dict[int, str]` maps every error number to its message. `fmt(code)` returns the formatted string used in `typer.echo`. All commands import from here instead of embedding literal strings.

### `pm/settings.py`

Runs at import time:
1. Computes `DATA_DIR`, `LOG_DIR`, `STATE_FILE` via `platformdirs`.
2. Creates those directories if missing.
3. Migrates the old in-package `processes_state.json` (pre-1.3) if it exists and the new path doesn't yet.
4. Instantiates the `StateManager` singleton as `state`.

Commands do `from pm.settings import state` to get the singleton. Tests patch this reference via `monkeypatch`.

### `pm/utils.py`

`StateManager` — the only class that touches the disk. Uses the Singleton pattern (`StateBase.__new__`) so all commands share one in-memory dict within a single CLI invocation. Key methods:

| Method | Purpose |
|--------|---------|
| `load_state()` | Read JSON from disk into `self.processes` |
| `save()` | Write `self.processes` to disk as pretty-printed JSON |
| `add_process(pid, data)` | Insert and save |
| `remove_process(pid)` | Delete and save |
| `update_process(pid, key, value)` | Patch one field and save |
| `bulk_update(data)` | Replace all entries and save |
| `get_by_name_or_pid(s)` | Lookup by PID string or process name |
| `get_a_group(name)` | Return all entries in a group |
| `get_parents_groupname()` | List of groups that have a parent |

### `pm/commands/`

Each file owns one conceptual area. All files follow the same pattern:

```python
from pm.settings import state       # shared singleton
from pm.schema import Status        # typed constants
from pm.errors import fmt           # error formatting

def my_command(...) -> None:
    """Typer-registered CLI function."""
    # business logic using state, psutil, subprocess
```

Internal helpers prefixed with `_` (e.g. `_create_process`, `_kill_group`) are called by other command modules to avoid duplication.

---

## Data Flow: `pm create "echo hi" --name test`

```
CLI input
  └── typer parses args
        └── create() in commands/create.py
              ├── validates relation/group rules (state.get_parents_groupname)
              ├── calls _popen() → subprocess.Popen(shell=True, start_new_session=True)
              ├── builds data dict
              └── state.add_process(pid, data) → writes JSON to disk

pm ls
  └── ls() in commands/ls.py
        ├── for each pid in state.processes:
        │     psutil.Process(pid).status() → resolve live status
        │     state.update_process(pid, "status", resolved)
        └── render Rich table (or JSON dump)

pm stop test
  └── stop() in commands/stop.py
        ├── state.get_by_name_or_pid("test") → (pid_str, data)
        ├── psutil.Process(pid).terminate()   → SIGTERM
        ├── psutil.wait_procs([proc], timeout=10)
        │     if alive → proc.kill()          → SIGKILL
        └── state.update_process(...) × 3     → status/exit_code/exited_at
```

---

## Key Design Decisions

**Singleton state manager** — Within one CLI invocation, all commands share one in-memory dict loaded at startup. `save()` is called after every mutation, so the disk is always up to date even if the process crashes mid-command.

**Module-level `state` import** — Commands do `from pm.settings import state`, binding the name at import time. This makes testing straightforward: `monkeypatch.setattr(pm.commands.create, "state", mock_state)` replaces the binding in one module without affecting others.

**`_create_process` as an internal helper** — The `create` CLI command and `manage.up` both need to spawn a process. The shared logic lives in `_create_process()`. CLI-specific concerns (echoing output, the `--foreground` wait) stay in `create()`.

**`pm stop` keeps entries in state** — After stopping, a process entry stays in state with `status=stopped`. This lets users inspect exit codes (`pm info`), restart (`pm restart`), or clean up explicitly (`pm cleanup` / `pm kill`). Only `pm kill` removes entries.

**Process detachment** — `start_new_session=True` (Unix) and `DETACHED_PROCESS` (Windows) ensure spawned processes outlive the `pm` process and don't receive terminal signals on close.
