"""
This module everything related to a process's creation.
The commands this module manages are
  - create
  - recreate
  - respawn
"""

import typer
import psutil
import subprocess
from pm.settings import state
from typing import Optional
from enum import Enum
from typing_extensions import Annotated


class Relation(str, Enum):
    PARENT = 'parent'
    CHILD = 'child'


def create(command: Annotated[str, typer.Argument()],
           name: Annotated[Optional[str], typer.Option("--name","-n")] = None,
           group: Annotated[Optional[str], typer.Option("--group","-g")] = None,
           relation: Annotated[Relation, typer.Option("--relation", "-r")] = Relation.PARENT,
           verbose: Annotated [bool, typer.Option("--verbose", "-v")] = False) -> int:

    """Create a new subprocess and optionally assign a name."""
    proc = subprocess.Popen(command, shell=True)
    pid = proc.pid

    if not group:
        group = str(pid)

    data = {
        "command": command,
        "name": name,
        "group": group,
        "relation": relation,
    }
    state.add_process(pid, data)
    if verbose:
        typer.echo(f"Process started with PID: {pid}")


def recreate():
    """Recreate all managed subprocesses."""
    new_processes = {}
    for pid, data in state.processes.items():
        proc = subprocess.Popen(data["command"], shell=True)
        new_processes[str(proc.pid)] = data
        typer.echo(f"Process {proc.pid} recreated with command: {data['command']}")

    state.bulk_update(new_processes)


def respawn():
    """Respawn processes that are in the JSON file but not running."""

    for pid, data in state.processes.items():
        if psutil.pid_exists(int(pid)):
            process = psutil.Process(int(pid))
            if not process.is_running():
                typer.echo(f"Process {pid} not running. Respawning...")
                process.resume()
                typer.echo(f"Process {pid} respawed.")

    typer.echo("Respawn complete.")