# Testing Guide

## Running the Tests

```bash
# All tests with verbose output
pytest tests/ -v

# Single file
pytest tests/test_create.py -v

# Single test
pytest tests/test_create.py::test_create_happy_path -v

# With coverage report
pytest tests/ --cov=pm --cov-report=term-missing
```

All 43 tests must pass before merging. CI runs the same suite across Python 3.10–3.13 on Ubuntu, macOS, and Windows.

---

## Test File Structure

```
tests/
├── conftest.py             # Shared fixtures (singleton reset, patched_state)
├── test_schema.py          # Unit tests for enums and ProcessRecord
├── test_state_manager.py   # Unit tests for StateManager CRUD
├── test_create.py          # CLI integration: pm create / pm start
├── test_kill.py            # CLI integration: pm kill
├── test_ls.py              # CLI integration: pm ls / pm status
└── test_stop.py            # CLI integration: pm stop
```

---

## Core Fixtures (`conftest.py`)

### `reset_singleton` (autouse)

Resets the `StateBase._instance` singleton before and after every test. Without this, the `StateManager` created in one test persists into the next.

```python
@pytest.fixture(autouse=True)
def reset_singleton():
    StateBase._instance = None
    yield
    StateBase._instance = None
```

This runs automatically for every test — you don't need to request it explicitly.

### `tmp_state`

A fresh `StateManager` backed by a temporary file. Use this for unit tests of `StateManager` itself where you don't need CLI invocation.

```python
def test_add(tmp_state):
    tmp_state.add_process(1, {"command": "echo", ...})
    assert "1" in tmp_state.get_processes()
```

### `patched_state`

A fresh `StateManager` backed by a temporary file, **patched into all command modules**. Use this for CLI integration tests.

```python
def test_create(patched_state):
    with patch("pm.commands.create.subprocess.Popen", return_value=mock_proc(1234)):
        result = runner.invoke(app, ["create", "echo hi"])
    assert "1234" in patched_state.get_processes()
```

Internally, `patched_state` calls `monkeypatch.setattr(mod, "state", sm)` for every command module. If you add a new module that imports `state`, add it to the list in `conftest.py`:

```python
import pm.commands.my_new
monkeypatch.setattr(pm.commands.my_new, "state", sm)
```

---

## Testing CLI Commands

Use `typer.testing.CliRunner` to invoke commands programmatically:

```python
from typer.testing import CliRunner
from pm.main import app

runner = CliRunner()

def test_something(patched_state):
    result = runner.invoke(app, ["ls", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
```

**Key properties of `result`:**

| Property | Type | Description |
|----------|------|-------------|
| `exit_code` | `int` | 0 = success, 1 = handled error, 2 = usage error |
| `output` | `str` | Everything printed to stdout |
| `exception` | `Exception \| None` | Unhandled exception (a bug if this is set) |

**Checking error cases:**

```python
result = runner.invoke(app, ["kill"])          # no args
assert result.exit_code != 0
assert "1100" in result.output                 # error code in message
```

---

## Mocking Subprocesses

Never spawn real subprocesses in tests. Mock `subprocess.Popen`:

```python
from unittest.mock import MagicMock, patch

def _mock_proc(pid=1234):
    proc = MagicMock()
    proc.pid = pid
    return proc

def test_create_happy_path(patched_state):
    with patch("pm.commands.create.subprocess.Popen", return_value=_mock_proc(1234)):
        result = runner.invoke(app, ["create", "echo hello"])
    assert result.exit_code == 0
    assert "1234" in patched_state.get_processes()
```

Patch `pm.commands.create.subprocess.Popen`, not `subprocess.Popen` globally. The `where` matters: patch the name as it is imported in the module under test.

---

## Mocking psutil

Never interact with real system processes in tests. Mock `psutil.Process`:

```python
def _mock_process(exit_code=0):
    proc = MagicMock()
    proc.children.return_value = []
    proc.wait.return_value = exit_code
    return proc

def test_kill_by_pid(patched_state):
    patched_state.add_process(100, {...})
    with patch("pm.commands.kill.psutil.Process", return_value=_mock_process()):
        result = runner.invoke(app, ["kill", "100"])
    assert "100" not in patched_state.get_processes()
```

For `psutil.NoSuchProcess` (process already gone):

```python
import psutil

def test_stop_already_dead(patched_state):
    patched_state.add_process(600, {...})
    with patch("pm.commands.stop.psutil.Process", side_effect=psutil.NoSuchProcess(600)):
        result = runner.invoke(app, ["stop", "ghost"])
    assert result.exit_code == 0
```

For `psutil.wait_procs` (used in `pm stop`):

```python
with patch("pm.commands.stop.psutil.wait_procs", return_value=([proc], [])):
    # ([gone], [alive]) — all gone, none alive
```

---

## Helper: Adding a Process to State

Many tests need a process in state before invoking a command. Use this pattern:

```python
def _add_proc(state, pid, name=None, group="g", relation="parent", status="running"):
    state.add_process(pid, {
        "command": "echo",
        "name": name,
        "group": group,
        "relation": relation,
        "status": status,
        "log_file": None,
        "autostart": True,
    })
```

---

## What Each Test File Covers

### `test_schema.py`

Pure unit tests with no I/O or mocking needed:

- `Relation` and `Status` enum string values
- `ProcessRecord` default field values
- `to_dict` round-trip
- `from_dict` with a full data dict
- `from_dict` with sparse/old-format data (backward compatibility)

### `test_state_manager.py`

Unit tests for `StateManager` using the `tmp_state` fixture:

- `add_process`, `remove_process`, `update_process`, `bulk_update`, `remove_all_processes`
- Disk persistence: create two separate `StateManager` instances on the same file and verify data survives
- `get_by_name_or_pid` by PID string, by name, not found
- `get_a_group` filtering
- `get_parents_groupname` and `is_group_exist`

### `test_create.py`

CLI tests using `patched_state` + `patch("pm.commands.create.subprocess.Popen")`:

- Happy path: process appears in state with correct PID
- Error 800: child with no `--group`
- Error 801: child with non-existent group
- Error 802: duplicate parent in same group
- `--log-file` option passes to state record
- `pm start` produces the same result as `pm create` (alias test)

### `test_kill.py`

CLI tests using `patched_state` + `patch("pm.commands.kill.psutil.Process")`:

- Error 1100: no argument given
- Error 1200: multiple arguments given
- Kill by PID: entry removed from state
- Kill unmanaged PID: graceful "not managed" message
- `--all`: all entries removed
- `--group`: only that group's entries removed; other groups unaffected

### `test_ls.py`

CLI tests using `patched_state` + `patch("pm.commands.ls.psutil.Process")`:

- Empty state: table renders without error
- `--json`: output is valid JSON containing the process entry
- `--group`: filters to matching group only
- `--running`: filters to `status == "running"` only
- Unknown group: error 1000
- `pm status` alias: produces same JSON as `pm ls`

### `test_stop.py`

CLI tests using `patched_state` + `patch("pm.commands.stop.psutil.Process")` + `patch("pm.commands.stop.psutil.wait_procs")`:

- Unknown process: error 1001
- Graceful stop by name: `terminate()` called, status set to `stopped`
- Graceful stop by PID
- `--force`: `kill()` called instead of `terminate()`
- Non-zero exit code: status set to `crashed`, `exit_code` stored
- Process already dead (NoSuchProcess): marked `stopped`, no error

---

## Adding Tests for a New Command

1. Create `tests/test_my_new.py`.
2. Import `runner` and `app`:
   ```python
   from typer.testing import CliRunner
   from pm.main import app
   runner = CliRunner()
   ```
3. If your command patches `state`, add the module to `conftest.py`'s `patched_state` fixture.
4. Mock any `subprocess` or `psutil` calls.
5. Test the happy path, at least one error path, and edge cases (process not found, already dead, etc.).
