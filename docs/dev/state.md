# State Management

## Overview

PMFlow stores all process metadata in a single JSON file. The `StateManager` class (`pm/utils.py`) owns all reads and writes. It is a singleton: all commands within a single CLI invocation share the same in-memory dict.

---

## State File Location

Resolved at startup by `pm/settings.py` using `platformdirs`:

| Platform | Path |
|----------|------|
| Linux | `~/.local/share/pmflow/processes_state.json` |
| macOS | `~/Library/Application Support/pmflow/processes_state.json` |
| Windows | `%APPDATA%\pmflow\processes_state.json` |

---

## JSON Schema

The file is a flat object keyed by PID (as a string):

```json
{
  "12345": {
    "command": "uvicorn app:app --host 0.0.0.0 --port 8000",
    "name": "api",
    "status": "running",
    "group": "backend",
    "relation": "parent",
    "log_file": "/home/user/.local/state/pmflow/api.log",
    "autostart": true,
    "created_at": "2026-06-27T09:14:32.001234+00:00",
    "exit_code": null,
    "exited_at": null
  },
  "12346": {
    "command": "celery -A tasks worker",
    "name": "worker",
    "status": "running",
    "group": "backend",
    "relation": "child",
    "log_file": "/home/user/.local/state/pmflow/worker.log",
    "autostart": true,
    "created_at": "2026-06-27T09:14:33.004567+00:00",
    "exit_code": null,
    "exited_at": null
  }
}
```

### Field Reference

| Field | Type | Set by | Description |
|-------|------|--------|-------------|
| `command` | `str` | `create` | The shell command as passed to `Popen` |
| `name` | `str \| null` | `create --name` | Human-readable label; used for lookup by `get_by_name_or_pid` |
| `status` | `str` | `ls`, `stop`, `kill` | One of the `Status` enum values (see below) |
| `group` | `str` | `create` | Group identifier; auto-generated for parents if not specified |
| `relation` | `str` | `create --relation` | `"parent"` or `"child"` |
| `log_file` | `str \| null` | `create --log-file` | Absolute path to stdout/stderr capture file |
| `autostart` | `bool` | `create --no-autostart` | Whether `pm recreate` should restart this process |
| `created_at` | `str` | `create`, `recreate` | ISO 8601 UTC timestamp |
| `exit_code` | `int \| null` | `stop`, `kill` | Exit code recorded when process exits |
| `exited_at` | `str \| null` | `stop` | ISO 8601 UTC timestamp when process exited |

### Status Values

Defined in `pm/schema.py` as `Status(str, Enum)`:

| Value | Set when |
|-------|---------|
| `running` | `create` succeeds; `ls` confirms process is alive |
| `paused` | `ls` sees `psutil.STATUS_STOPPED` |
| `stopped` | `stop` completes and exit code is 0 or None |
| `crashed` | `stop` completes and exit code is non-zero |
| `unknown` | `ls` cannot find the PID and the stored status was `running` |

`stopped` and `crashed` are only set by `pm stop`. If a process dies without `pm stop` being called (crash, OOM kill), the next `pm ls` sets it to `unknown`.

---

## `ProcessRecord` Dataclass

`pm/schema.py` defines a typed dataclass that mirrors the JSON schema. It is **not** currently used for persistence (state is stored as plain dicts) but is used for type checking, documentation, and deserialization:

```python
from pm.schema import ProcessRecord

rec = ProcessRecord.from_dict(pid=12345, data=raw_dict)
# rec.status, rec.log_file, etc. are typed
```

`from_dict` uses `.get()` with defaults for every field, so it safely loads old state files that predate the 1.3 schema.

If you add a new field to the state schema, add it to `ProcessRecord` and provide a sensible default in `from_dict`. Also update the JSON schema table above.

---

## `StateManager` API

```python
from pm.settings import state  # singleton instance

# Read
procs: dict = state.get_processes()
entry: tuple | None = state.get_by_name_or_pid("api")   # (pid_str, data) or None
group: dict = state.get_a_group("backend")
parents: list[str] = state.get_parents_groupname()
exists: bool = state.is_exist("12345")
group_taken: bool = state.is_group_exist("backend")

# Write (each call persists to disk immediately)
state.add_process(pid, data_dict)
state.remove_process(pid)
state.remove_all_processes()
state.update_process(pid, "status", "stopped")
state.bulk_update({"12345": {...}, "12346": {...}})
```

Every write method calls `self.save()` before returning. There is no dirty-flag or deferred flush — the disk is always consistent with memory after any mutation.

---

## Singleton Pattern

`StateBase` implements `__new__` to ensure only one `StateManager` instance exists per Python process:

```python
class StateBase:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

**In tests**, the singleton must be reset between test functions or the first test's state bleeds into the next. `conftest.py` handles this with an `autouse` fixture:

```python
@pytest.fixture(autouse=True)
def reset_singleton():
    StateBase._instance = None
    yield
    StateBase._instance = None
```

---

## State Migration (pre-1.3 installs)

Before v1.3, the state file lived at `pm/processes_state.json` inside the installed package. On first startup after upgrading, `pm/settings.py` copies the old file to the new user data location if:

1. The old file exists at the package location.
2. The new user data path does not yet exist.

After migration the old file is left in place (not deleted) so a downgrade can still find it.

---

## Extending the Schema

To add a new field (e.g. `restart_count`):

1. Add it to `ProcessRecord` in `pm/schema.py` with a default:
   ```python
   restart_count: int = 0
   ```
2. Add it to `from_dict`:
   ```python
   restart_count=data.get('restart_count', 0),
   ```
3. Set it when creating a process in `_create_process` (`commands/create.py`):
   ```python
   data = {
       ...
       "restart_count": 0,
   }
   ```
4. Increment it in `restart` (`commands/stop.py`).
5. Update the JSON schema table in this file.
6. Add a test in `tests/test_state_manager.py`.
