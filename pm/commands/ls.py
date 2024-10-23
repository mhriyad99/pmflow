"""
This module manages handles output presentation of the process's.
The command it manages are
    - ls
"""

import typer
import psutil
from rich import Console
from rich.table import Table
from pm.settings import state


def ls():
    """List all managed subprocesses."""
    table = Table(title="Processes")
    table.add_column("PID", justify="right", style="cyan")
    table.add_column("Name", justify="right", style="magenta")
    table.add_column("Status", justify="right", style="green")
    table.add_column("Command", justify="right", style="yellow")

    for pid, properties in state.processes.items():
        try:
            process = psutil.Process(int(pid))
            if process.status() == psutil.STATUS_STOPPED:
                status = 'paused'
            else:
                status = 'running'
        except psutil.NoSuchProcess:
            status = "doesn't exist"

        table.add_row(pid, properties["name"], status, properties["command"])

    console = Console()
    console.print(table)