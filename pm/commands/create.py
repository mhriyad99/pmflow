"""
Process creation commands: create, recreate, respawn
"""

import sys
import random
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

import typer
import psutil
from typing_extensions import Annotated

from pm.settings import state, LOG_DIR
from pm.schema import Relation, Status
from pm.errors import fmt


def _open_log(log_file: Optional[str]):
    if not log_file:
        return None
    path = Path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    return open(path, "a")


def _popen(command: str, log_handle, foreground: bool = False) -> subprocess.Popen:
    kwargs: dict = {"shell": True}
    if log_handle:
        kwargs["stdout"] = log_handle
        kwargs["stderr"] = log_handle
    if not foreground:
        if sys.platform == "win32":
            kwargs["creationflags"] = (
                subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            kwargs["start_new_session"] = True
    return subprocess.Popen(command, **kwargs)


def _create_process(
    command: str,
    name: Optional[str],
    group: Optional[str],
    relation: str,
    log_file: Optional[str],
    autostart: bool,
    foreground: bool = False,
) -> tuple:
    """Core process creation logic. Returns (pid, proc)."""
    if relation == Relation.CHILD:
        if not group:
            typer.echo(fmt(800))
            raise typer.Exit(code=1)
        if group not in state.get_parents_groupname():
            typer.echo(fmt(801))
            raise typer.Exit(code=1)

    if relation == Relation.PARENT:
        if not group:
            group = f"group-{random.randint(1, 1_000_000)}"
        elif state.is_group_exist(group):
            typer.echo(fmt(802))
            raise typer.Exit(code=1)

    log_handle = _open_log(log_file)
    proc = _popen(command, log_handle, foreground=foreground)

    data = {
        "command": command,
        "name": name,
        "status": Status.RUNNING,
        "group": group,
        "relation": relation,
        "log_file": log_file,
        "autostart": autostart,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "exit_code": None,
        "exited_at": None,
    }
    state.add_process(proc.pid, data)
    return proc.pid, proc


def create(
    command: Annotated[str, typer.Argument()],
    name: Annotated[Optional[str], typer.Option("--name", "-n")] = None,
    group: Annotated[Optional[str], typer.Option("--group", "-g")] = None,
    relation: Annotated[Relation, typer.Option("--relation", "-r")] = Relation.PARENT,
    foreground: Annotated[bool, typer.Option("--foreground", "-f")] = False,
    log_file: Annotated[Optional[str], typer.Option("--log-file", "-l")] = None,
    no_autostart: Annotated[bool, typer.Option("--no-autostart")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Create a new subprocess and optionally assign a name."""
    pid, proc = _create_process(
        command=command,
        name=name,
        group=group,
        relation=relation,
        log_file=log_file,
        autostart=not no_autostart,
        foreground=foreground,
    )
    typer.echo(f"Process started with PID: {pid}")
    if verbose and log_file:
        typer.echo(f"  Log: {log_file}")
    if foreground:
        proc.wait()
        typer.echo(f"Process {pid} has stopped.")


def recreate() -> None:
    """Recreate all managed subprocesses from stored commands."""
    new_processes = {}
    for pid, data in state.processes.items():
        log_handle = _open_log(data.get("log_file"))
        proc = _popen(data["command"], log_handle)
        updated = dict(data)
        updated.update({
            "status": Status.RUNNING,
            "exit_code": None,
            "exited_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        new_processes[str(proc.pid)] = updated
        typer.echo(f"Process {proc.pid} recreated with command: {data['command']}")
    state.bulk_update(new_processes)


def respawn() -> None:
    """Respawn processes that are paused."""
    for pid, data in state.processes.items():
        if psutil.pid_exists(int(pid)):
            proc = psutil.Process(int(pid))
            if proc.status() == psutil.STATUS_STOPPED:
                typer.echo(f"Process {pid} is paused. Respawning...")
                proc.resume()
                state.update_process(pid, "status", Status.RUNNING)
                typer.echo(f"Process {pid} respawned.")
    typer.echo("Respawn complete.")
