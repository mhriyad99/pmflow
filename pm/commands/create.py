"""
This module everything related to a process's creation.
The commands this module manages are
  - create
  - recreate
  - respawn
"""

import typer
import psutil
import random
import subprocess
from pm.settings import state
from typing import Optional
from typing_extensions import Annotated
from pm.schema import Relation

def create(command: Annotated[str, typer.Argument()],
           name: Annotated[Optional[str], typer.Option("--name","-n")] = None,
           group: Annotated[Optional[str], typer.Option("--group","-g")] = None,
           relation: Annotated[Relation, typer.Option("--relation", "-r")] = Relation.PARENT,
           verbose: Annotated [bool, typer.Option("--verbose", "-v")] = False) -> int:

    """Create a new subprocess and optionally assign a name."""

    if relation == Relation.CHILD:
        if not group:
            typer.echo(f"Error 800: Please specify an existing group of a parent process")
            raise typer.Exit(code=1)
        elif group not in state.get_parents_groupname():
            typer.echo(f"Error 801: No parent group with this group name exist. "
                       f"Please specify an existing group of a parent process")
            raise typer.Exit(code=1)

    if relation == Relation.PARENT:
        if not group:
            group = f"group-{random.randint(1, 1000000)}"
        elif state.is_group_exist(group):
            typer.echo(f"Error 802: A group can have only one parent process.")
            raise typer.Exit(code=1)

    proc = subprocess.Popen(command, shell=True)
    pid = proc.pid



    data = {
        "command": command,
        "name": name,
        "status": "running",
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