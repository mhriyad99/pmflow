#!/usr/bin/env python3
import os
import signal
import sys

import typer
import json
import psutil
import subprocess
from rich.console import Console
from rich.table import Table

app = typer.Typer()

def load_state():
    """Load processes state from a file."""
    global processes
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as file:
            processes = json.load(file)

processes = {}
STATE_FILE = os.getcwd() + '/processes_state.json'
load_state()

@app.command()
def greet(name: str):
    print(f"Hello, {name}! How are you?")

# @app.command()
# def create(command: str):
#     id = str(uuid.uuid4())
#     processes[id] = command
#     save_state()
#     typer.echo(f"Process {id} started with command: {command}")

@app.command()
def create(command: str, name: str = None) -> int:
    """Create a new subprocess and optionally assign a name."""
    proc = subprocess.Popen(command, shell=True)
    pid = proc.pid
    processes[pid] = {
        "command": command,
        "name": name,
        "status": "running"
    }
    save_state()
    typer.echo(f"{pid}")

    # Return the PID for external usage
    return pid

@app.command()
def state_load():
    # load_state()
    typer.echo(json.dumps(processes))

@app.command()
def state_location():
    typer.echo(STATE_FILE)

@app.command()
def pause(pid: int):
    """Pause a subprocess and all its children by PID."""
    pid_str = str(pid)
    if pid_str in processes:
        try:
            process = psutil.Process(int(pid))
            all_processes = [process] + process.children(recursive=True)
            for proc in all_processes:
                proc.send_signal(signal.SIGSTOP)
            # Update process status to 'paused' and save state
            processes[pid_str] = {
                "command": processes[pid_str],
                "status": "paused"
            }
            save_state()
            typer.echo(f"Process {pid} and its child processes have been paused.")
        except psutil.NoSuchProcess:
            typer.echo("Process not found.")
    else:
        typer.echo("Process not managed by this tool.")


@app.command()
def kill(pid: int):
    """Kill a subprocess by PID."""
    if str(pid) in processes:
        try:
            process = psutil.Process(pid)
            for child in process.children(recursive=True):
                child.terminate()
            process.terminate()
            processes.pop(str(pid), None)
            save_state()
            typer.echo(f"Process {pid} killed.")
        except psutil.NoSuchProcess:
            processes.pop(str(pid), None)
            save_state()
            typer.echo("Process not found. Removed from the state file.")
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

    for pid, properties in processes.items():
        typer.echo(f"How are you?")
        process = psutil.Process(int(pid))
        status = 'running' if process.is_running() else 'paused'
        table.add_row(pid, properties["name"], status, properties["command"])

    console = Console()
    console.print(table)

@app.command()
def recreate():
    """Recreate all managed subprocesses."""
    load_state()
    for pid, command in processes.items():
        proc = subprocess.Popen(command, shell=True)
        processes[proc.pid] = command
        typer.echo(f"Process {proc.pid} recreated with command: {command}")
    save_state()

@app.command()
def respawn():
    """Respawn processes that are in the JSON file but not running."""
    load_state()
    new_processes = {}
    for pid, command in processes.items():
        if not psutil.pid_exists(int(pid)):
            typer.echo(f"Process {pid} not running. Respawning...")
            proc = subprocess.Popen(command, shell=False)
            new_processes[proc.pid] = command
            typer.echo(f"Process {proc.pid} respawned with command: {command}")
        else:
            new_processes[int(pid)] = command
    processes.clear()
    processes.update(new_processes)
    save_state()
    typer.echo("Respawn complete.")


@app.command()
def kill_all():
    """Kill all managed processes and clear the state."""
    load_state()
    for pid in processes.keys():
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

    processes.clear()
    save_state()
    typer.echo("All processes have been terminated and removed from the state.")

def save_state():
    """Save current processes state to a file."""
    with open(STATE_FILE, "w") as file:
        json.dump(processes, file)


def signal_handler(sig, frame):
    typer.echo("Ctrl+C pressed. Terminating all managed processes...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    app()
