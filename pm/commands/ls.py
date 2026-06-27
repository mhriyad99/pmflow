"""
Process listing command: ls (aliased as status)
"""

import json

import typer
import psutil
from rich.console import Console
from rich.table import Table
from rich.text import Text
from typing_extensions import Annotated

from pm.settings import state
from pm.schema import Status
from pm.errors import fmt

_STATUS_STYLE = {
    Status.RUNNING: "green",
    Status.PAUSED: "yellow",
    Status.STOPPED: "cyan",
    Status.CRASHED: "red",
    Status.UNKNOWN: "dim",
}


def _resolve_status(pid: str, stored: str) -> str:
    try:
        proc = psutil.Process(int(pid))
        if proc.status() == psutil.STATUS_STOPPED:
            return Status.PAUSED
        return Status.RUNNING
    except psutil.NoSuchProcess:
        if stored in (Status.STOPPED, Status.CRASHED):
            return stored
        return Status.UNKNOWN


def ls(
    json_output: Annotated[bool, typer.Option("--json", "-j")] = False,
    group_name: Annotated[str, typer.Option("--group", "-g")] = None,
    running: Annotated[bool, typer.Option("--running", "-r")] = False,
) -> None:
    """List all managed subprocesses."""
    for pid, props in state.get_processes().items():
        status = _resolve_status(pid, props.get("status", Status.UNKNOWN))
        state.update_process(pid, "status", status)

    if group_name:
        process_dict = state.get_a_group(group_name)
        if not process_dict:
            typer.echo(fmt(1000))
            raise typer.Exit(code=1)
    else:
        process_dict = state.get_processes()

    if running:
        process_dict = {p: d for p, d in process_dict.items() if d["status"] == Status.RUNNING}

    if json_output:
        typer.echo(json.dumps(process_dict, indent=2))
        return

    table = Table()
    table.add_column("PID", justify="center", style="#00ffee")
    table.add_column("Name", justify="center", style="#f7d59e")
    table.add_column("Status", justify="center")
    table.add_column("Group", justify="center", style="#00ffee")
    table.add_column("Relation", justify="center", style="#f700ff")
    table.add_column("Command", justify="center", style="#00ff26")

    for pid, props in process_dict.items():
        st = props.get("status", Status.UNKNOWN)
        style = _STATUS_STYLE.get(st, "white")
        status_cell = Text(st, style=style)
        table.add_row(
            pid,
            props.get("name") or "",
            status_cell,
            props.get("group") or "",
            props.get("relation") or "",
            props.get("command") or "",
        )

    Console().print(table)
