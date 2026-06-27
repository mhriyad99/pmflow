"""
Process detail view: info
"""

from datetime import datetime, timezone

import typer
import psutil
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from pm.settings import state
from pm.errors import fmt


def info(
    name_or_pid: Annotated[str, typer.Argument(help="Process name or PID")],
) -> None:
    """Show detailed information about a single process."""
    result = state.get_by_name_or_pid(name_or_pid)
    if not result:
        typer.echo(fmt(1001))
        raise typer.Exit(code=1)

    pid_str, data = result
    pid = int(pid_str)

    cpu_str = mem_str = uptime_str = "N/A"
    try:
        proc = psutil.Process(pid)
        cpu_str = f"{proc.cpu_percent(interval=0.1):.1f}%"
        mem_str = f"{proc.memory_info().rss / 1024 / 1024:.1f} MB"
        created = datetime.fromtimestamp(proc.create_time(), tz=timezone.utc)
        delta = datetime.now(timezone.utc) - created
        hours, rem = divmod(int(delta.total_seconds()), 3600)
        mins = rem // 60
        uptime_str = f"{hours}h {mins}m"
    except psutil.NoSuchProcess:
        pass

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column()

    rows = [
        ("Name", data.get("name") or "—"),
        ("PID", pid_str),
        ("Status", data.get("status", "unknown")),
        ("Command", data.get("command", "")),
        ("Group", data.get("group", "")),
        ("Relation", data.get("relation", "")),
        ("Autostart", str(data.get("autostart", True))),
        ("Log file", data.get("log_file") or "—"),
        ("Created at", data.get("created_at") or "—"),
        ("Exited at", data.get("exited_at") or "—"),
        ("Exit code", str(data.get("exit_code")) if data.get("exit_code") is not None else "—"),
        ("Uptime", uptime_str),
        ("CPU", cpu_str),
        ("Memory (RSS)", mem_str),
    ]
    for label, value in rows:
        table.add_row(label, value)

    Console().print(table)
