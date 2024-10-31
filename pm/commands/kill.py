"""
This module is related to stopping a process's from running or deleting it altogether
The commands it manages are
    - pause
    - kill
"""

import typer
import psutil
import signal
from typing import Optional
from typing_extensions import Annotated
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


def kill(pid: Annotated[Optional[int], typer.Argument()] = 0,
         group: Annotated[Optional[str], typer.Option("--group", "-g")] = None,
        child: Annotated[Optional[bool], typer.Option("--child", "-c")] = False,
         all: Annotated[Optional[bool], typer.Option("--all", "-a")] = False,):
    """
    Kill a subprocess by PID, group name.

    params:
    pid: int -> kill a process by it's pid.
    group: str -> kill a process by it's group name.'
    child: bool -> kill all child process of a group. This can only be used with --group or -g.
    all: bool -> kill all existing process.

    """

    # validating arguments so that only one argument is given otherwise throw error
    args_given = sum([pid != 0, group is not None, all is not False])

    if args_given == 0:
        typer.echo("Error 1100: You must specify exactly one of: PID, group, or --all.", err=True)
        raise typer.Exit(code=1)

    if args_given > 1:
        typer.echo("Error 1200: You can only specify one of: PID, group, or --all.", err=True)
        raise typer.Exit(code=1)

    # Delete process with the flag given
    # For pid
    if pid:
        pid_str = str(pid)

        if pid_str in state.get_processes().keys():
            if state.get_processes()[pid_str]["relation"] == "parent":
                typer.echo(f"Process {pid} is a parent process. Killing it with all it's children...")
                process_group = state.get_a_group(state.get_processes()[pid_str]["group"])
                if process_group:
                    kill_group_process(process_group)
                    for pid in process_group.keys():
                        state.remove_process(pid)
            else:
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

    # For group flag --group or -g
    if group:
        process_group = state.get_a_group(group)

        if child:
            process_group = {pid: data for pid, data in process_group.items() if data["relation"] == "child"}

        if process_group:
            kill_group_process(process_group)
            for pid in process_group.keys():
                state.remove_process(pid)

    # For all flag --all or -a
    if all:
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


def kill_group_process(processes: dict):

    for pid in processes.keys():
        try:
            process = psutil.Process(int(pid))
            for child in process.children(recursive=True):
                child.terminate()
            process.terminate()
            typer.echo(f"Process {pid} terminated.")
        except psutil.NoSuchProcess:
            typer.echo(f"Process {pid} not found. Removed from state.")
        except Exception as e:
            typer.echo(f"Error terminating process {pid}: {str(e)}")
