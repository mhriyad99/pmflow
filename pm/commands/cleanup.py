"""
Stale state cleanup command: cleanup
"""

import psutil
import typer

from pm.settings import state


def cleanup() -> None:
    """Remove entries for processes that no longer exist."""
    stale = [
        pid_str
        for pid_str in list(state.get_processes())
        if not psutil.pid_exists(int(pid_str))
    ]

    if not stale:
        typer.echo("No stale processes found.")
        return

    for pid_str in stale:
        state.remove_process(pid_str)
        typer.echo(f"Removed stale process {pid_str}.")

    typer.echo(f"Cleaned up {len(stale)} stale process(es).")
