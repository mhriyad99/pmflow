#!/usr/bin/env python3
import os
import signal
import sys

import typer
import psutil
import subprocess
from rich.console import Console
from rich.table import Table
from pm.utils import StateManager

app = typer.Typer()

STATE_FILE = os.path.join(os.path.dirname(__file__), 'processes_state.json')
state = StateManager(STATE_FILE)

@app.command()
def greet(name: str):
    print(f"Hello, {name}!")


@app.command()
def create(command: str, name: str = None) -> int:
    """Create a new subprocess and optionally assign a name."""
    proc = subprocess.Popen(command, shell=True)
    pid = proc.pid
    data = {
        "command": command,
        "name": name,
    }
    state.add_process(pid, data)
    typer.echo(f"{pid}")


@app.command()
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


@app.command()
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

@app.command()
def recreate():
    """Recreate all managed subprocesses."""
    new_processes = {}
    for pid, data in state.processes.items():
        proc = subprocess.Popen(data["command"], shell=True)
        new_processes[str(proc.pid)] = data
        typer.echo(f"Process {proc.pid} recreated with command: {data['command']}")

    state.bulk_update(new_processes)


@app.command()
def respawn_all():
    """Respawn processes that are in the JSON file but not running."""

    for pid, data in state.processes.items():
        if psutil.pid_exists(int(pid)):
            process = psutil.Process(int(pid))
            if not process.is_running():
                typer.echo(f"Process {pid} not running. Respawning...")
                process.resume()
                typer.echo(f"Process {pid} respawed.")

    typer.echo("Respawn complete.")


@app.command()
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


@app.command()
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



def signal_handler(sig, frame):
    typer.echo("Ctrl+C pressed. Terminating all managed processes...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    app()
