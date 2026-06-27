"""
Log streaming command: logs
"""

import time
from pathlib import Path

import typer
from typing_extensions import Annotated

from pm.settings import state
from pm.errors import fmt


def logs(
    name_or_pid: Annotated[str, typer.Argument(help="Process name or PID")],
    lines: Annotated[int, typer.Option("--lines", "-n", help="Number of lines to show")] = 20,
    follow: Annotated[bool, typer.Option("--follow", "-f", help="Stream new output (like tail -f)")] = False,
) -> None:
    """Show the last N lines of a process log file."""
    result = state.get_by_name_or_pid(name_or_pid)
    if not result:
        typer.echo(fmt(1001))
        raise typer.Exit(code=1)

    _, data = result
    log_file = data.get("log_file")

    if not log_file or not Path(log_file).exists():
        typer.echo(fmt(1300))
        raise typer.Exit(code=1)

    path = Path(log_file)

    with open(path, "r") as f:
        content = f.readlines()

    for line in content[-lines:]:
        typer.echo(line, nl=False)

    if follow:
        typer.echo(f"\n--- Following {path} (Ctrl+C to stop) ---")
        try:
            with open(path, "r") as f:
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if line:
                        typer.echo(line, nl=False)
                    else:
                        time.sleep(0.1)
        except KeyboardInterrupt:
            pass
