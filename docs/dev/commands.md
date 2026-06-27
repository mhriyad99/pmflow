# Command System

## How Commands Are Registered

`pm/main.py` creates a single `typer.Typer` instance and registers functions onto it:

```python
app = typer.Typer(help="PMFlow — lightweight process manager")

app.command("create")(create)
app.command("start")(create)   # alias — same function, different name
```

Aliases are created by registering the same function under two names. The function's docstring becomes the help text for both.

The `pm` console script maps to `pm.main:app` via `pyproject.toml`:

```toml
[project.scripts]
pm = "pm.main:app"
```

---

## Anatomy of a Command

Every command follows this structure:

```python
# pm/commands/my_command.py

import typer
import psutil
from typing_extensions import Annotated
from typing import Optional

from pm.settings import state     # StateManager singleton
from pm.schema import Status      # typed constants
from pm.errors import fmt         # error message helper


def my_command(
    # Required positional argument
    name_or_pid: Annotated[str, typer.Argument(help="Process name or PID")],

    # Optional flags
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
    count: Annotated[Optional[int], typer.Option("--count", "-n")] = None,
) -> None:
    """One-line summary shown in pm --help."""

    # 1. Validate / look up
    result = state.get_by_name_or_pid(name_or_pid)
    if not result:
        typer.echo(fmt(1001))
        raise typer.Exit(code=1)

    pid_str, data = result

    # 2. Do work
    # ...

    # 3. Persist
    state.update_process(pid_str, "status", Status.STOPPED)

    # 4. Report
    typer.echo(f"Done: {pid_str}")
```

### Parameter Annotation Style

All parameters use `Annotated` from `typing_extensions`. This is the Typer 0.12 preferred style and keeps type hints and CLI metadata co-located:

```python
# Positional argument
command: Annotated[str, typer.Argument()]

# Optional argument (can be omitted, defaults to 0)
pid: Annotated[Optional[int], typer.Argument()] = 0

# String option
name: Annotated[Optional[str], typer.Option("--name", "-n")] = None

# Boolean flag (passing --verbose sets it True; default False)
verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False

# Negation flag (passing --no-autostart sets it True; default False)
no_autostart: Annotated[bool, typer.Option("--no-autostart")] = False
```

> **Click 8.1.x constraint:** Do not use `Annotated[bool, typer.Option()]` (no explicit name) for boolean parameters. With Click < 8.2, Typer auto-generates `--flag/--no-flag` pairs correctly, but the project is pinned to `click<8.2.0` to avoid a `make_metavar` signature incompatibility. Explicit names like `typer.Option("--verbose")` are safe.

---

## Command Map

| CLI name | Function | File |
|----------|----------|------|
| `pm create` | `create()` | `commands/create.py` |
| `pm start` | `create()` | alias |
| `pm recreate` | `recreate()` | `commands/create.py` |
| `pm respawn` | `respawn()` | `commands/create.py` |
| `pm stop` | `stop()` | `commands/stop.py` |
| `pm restart` | `restart()` | `commands/stop.py` |
| `pm kill` | `kill()` | `commands/kill.py` |
| `pm pause` | `pause()` | `commands/kill.py` |
| `pm ls` | `ls()` | `commands/ls.py` |
| `pm status` | `ls()` | alias |
| `pm info` | `info()` | `commands/info.py` |
| `pm logs` | `logs()` | `commands/logs.py` |
| `pm cleanup` | `cleanup()` | `commands/cleanup.py` |
| `pm up` | `up()` | `commands/manage.py` |
| `pm down` | `down()` | `commands/manage.py` |
| `pm version` | `version()` | `main.py` (inline) |

---

## Shared Internal Helpers

Some logic is extracted into underscore-prefixed helpers so it can be called by multiple command modules without creating circular imports.

### `_create_process` (`commands/create.py`)

Core process-spawning logic. Used by `create()` and `manage.up()`.

```python
pid, proc = _create_process(
    command="uvicorn app:app",
    name="api",
    group="backend",
    relation="parent",
    log_file="logs/api.log",
    autostart=True,
    foreground=False,
)
```

Returns `(pid: int, proc: subprocess.Popen)`. The `proc` object is only needed for `foreground` mode (`proc.wait()`).

### `_popen` (`commands/create.py`)

Wraps `subprocess.Popen` with detachment flags and optional log redirection:

```python
proc = _popen(command, log_handle, foreground=False)
```

- **Unix:** `start_new_session=True` → puts the child in a new session; terminal close does not kill it.
- **Windows:** `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` flags.
- **foreground=True:** No detachment flags; `Popen` inherits the terminal.

### `_open_log` (`commands/create.py`)

Opens a log file for appending, creating parent directories if needed. Returns `None` if `log_file` is `None`.

### `_kill_group` / `_kill_single` (`commands/kill.py`)

Terminate one process or a whole group and handle `psutil.NoSuchProcess` gracefully.

### `_mark_exited` (`commands/stop.py`)

Updates `status`, `exit_code`, and `exited_at` in state after a process is stopped.

---

## Adding a New Command

1. **Create the function** in the appropriate file (or a new file in `pm/commands/`):

   ```python
   # pm/commands/my_new.py
   import typer
   from pm.settings import state
   from pm.errors import fmt

   def my_new(...) -> None:
       """Short description for pm --help."""
       ...
   ```

2. **Register it in `pm/main.py`**:

   ```python
   from pm.commands.my_new import my_new
   app.command("my-new")(my_new)
   ```

3. **Add an error code** in `pm/errors.py` if the command can fail with a known error:

   ```python
   ERROR_CODES = {
       ...
       1500: "My new error description",
   }
   ```

4. **Write tests** in `tests/test_my_new.py` using the `patched_state` fixture (see [Testing](testing.md)).

5. **Update the README** command reference table and the `docs/dev/commands.md` command map.

---

## Error Handling Pattern

Commands that can fail in a known way print the error via `typer.echo(fmt(code))` and exit with code 1:

```python
result = state.get_by_name_or_pid(name_or_pid)
if not result:
    typer.echo(fmt(1001))
    raise typer.Exit(code=1)
```

`raise typer.Exit(code=1)` is the correct way to exit with a non-zero code in Typer — it raises an exception that Typer's runner catches and converts to a real exit code.

Unexpected errors (bugs, psutil exceptions for edge cases) are allowed to bubble up as unhandled exceptions. Typer will print the traceback in debug mode.
