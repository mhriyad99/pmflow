"""
This module manages handles output presentation of the process's.
The command it manages are
    - ls
"""

import typer
import psutil
import json
from rich.console import Console
from rich.table import Table
from pm.settings import state
from typing_extensions import Annotated


def ls(json_output: Annotated[bool, typer.Option("--json", "-j")] = False) -> None:
    """List all managed subprocesses."""

    if json_output:
        json_output = json.dumps(state.get_processes())
        typer.echo(json_output)

    else:
        table = Table()
        table.add_column("PID", justify="center", style="#00ffee")
        table.add_column("Name", justify="center", style="#f7d59e")
        table.add_column("Status", justify="center", style="#e2fa2a")
        table.add_column("Group", justify="center", style="#00ffee")
        table.add_column("Relation", justify="center", style="#f700ff")
        table.add_column("Command", justify="center", style="#00ff26")


        for pid, properties in state.get_processes().items():
            try:
                process = psutil.Process(int(pid))
                if process.status() == psutil.STATUS_STOPPED:
                    status = 'paused'
                else:
                    status = 'running'
            except psutil.NoSuchProcess:
                status = "doesn't exist"

            table.add_row(pid, properties["name"], status, properties["group"],
                          properties["relation"],properties["command"])

        console = Console()
        console.print(table)