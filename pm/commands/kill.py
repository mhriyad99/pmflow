"""
This module is related to stopping a process's from running or deleting it altogether
The commands it manages are
    - pause
    - kill
    - kill-all
"""

import typer
import psutil
import signal
from pm.settings import state


def pause(pid: int):
    """Pause a subprocess and all its children by PID."""
    pid_str = str(pid)
    if pid_str in state.processes:
        try:
            process = psutil.Process(int(pid))
            all_processes = [process] + process.children(recursive=True)
            for proc in all_processes:
                proc.send_signal(signal.SIGSTOP)
            typer.echo(f"Process {pid} and its child processes have been paused.")
        except psutil.NoSuchProcess:
            typer.echo("Process not found.")
    else:
        typer.echo("Process not managed by this tool.")


def kill(pid: int):
    """Kill a subprocess by PID."""
    pid_str = str(pid)
    if pid_str in state.processes:
        try:
            process = psutil.Process(int(pid))
            for child in process.children(recursive=True):
                child.terminate()
            process.terminate()
            state.remove_process(pid_str)
            typer.echo(f"Process {pid} killed.")
        except psutil.NoSuchProcess:
            state.remove_process(pid_str)
            typer.echo("Process not found. Removed from the state file.")
    else:
        typer.echo("Process not managed by this tool.")


def kill_all():
    """Kill all managed processes and clear the state."""

    for pid in state.processes.keys():
        try:
            process = psutil.Process(int(pid))
            for child in process.children(recursive=True):
                child.terminate()
            process.terminate()
            typer.echo(f"Process {pid} terminated.")
        except psutil.NoSuchProcess:
            typer.echo(f"Process {pid} not found.")
        except Exception as e:
            typer.echo(f"Error terminating process {pid}: {str(e)}")

    state.remove_all_processes()
    typer.echo("All processes have been terminated and removed from the state.")