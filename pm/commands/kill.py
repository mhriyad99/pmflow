"""
Immediate process removal commands: pause, kill
For graceful termination use: pm stop
"""

import signal
from typing import Optional

import typer
import psutil
from typing_extensions import Annotated

from pm.settings import state
from pm.errors import fmt


def pause(pid: int) -> None:
    """Pause a subprocess and all its children by PID."""
    pid_str = str(pid)
    if pid_str not in state.processes:
        typer.echo("Process not managed by this tool.")
        return
    try:
        process = psutil.Process(pid)
        for proc in [process] + process.children(recursive=True):
            proc.send_signal(signal.SIGSTOP)
        typer.echo(f"Process {pid} and its children have been paused.")
    except psutil.NoSuchProcess:
        typer.echo("Process not found.")


def kill(
    pid: Annotated[Optional[int], typer.Argument()] = 0,
    group: Annotated[Optional[str], typer.Option("--group", "-g")] = None,
    child: Annotated[Optional[bool], typer.Option("--child", "-c")] = False,
    all: Annotated[Optional[bool], typer.Option("--all", "-a")] = False,
) -> None:
    """
    Immediately terminate a process and remove it from state.

    Specify one of: PID, --group, or --all.
    For graceful shutdown use: pm stop
    """
    args_given = sum([pid != 0, group is not None, all is not False])

    if args_given == 0:
        typer.echo(fmt(1100), err=True)
        raise typer.Exit(code=1)

    if args_given > 1:
        typer.echo(fmt(1200), err=True)
        raise typer.Exit(code=1)

    if pid:
        pid_str = str(pid)
        if pid_str not in state.get_processes():
            typer.echo("Process not managed by this tool.")
            return
        if state.get_processes()[pid_str]["relation"] == "parent":
            typer.echo(f"Process {pid} is a parent. Killing it with all its children...")
            group_name = state.get_processes()[pid_str]["group"]
            process_group = state.get_a_group(group_name)
            _kill_group(process_group)
            for g_pid in process_group:
                state.remove_process(g_pid)
        else:
            _kill_single(pid, pid_str)

    if group:
        process_group = state.get_a_group(group)
        if child:
            process_group = {p: d for p, d in process_group.items() if d["relation"] == "child"}
        if process_group:
            _kill_group(process_group)
            for g_pid in process_group:
                state.remove_process(g_pid)

    if all:
        for p in list(state.processes):
            try:
                proc = psutil.Process(int(p))
                for ch in proc.children(recursive=True):
                    ch.terminate()
                proc.terminate()
                typer.echo(f"Process {p} terminated.")
            except psutil.NoSuchProcess:
                typer.echo(f"Process {p} not found.")
            except Exception as exc:
                typer.echo(f"Error terminating {p}: {exc}")
        state.remove_all_processes()
        typer.echo("All processes terminated and removed from state.")


def _kill_single(pid: int, pid_str: str) -> None:
    try:
        proc = psutil.Process(pid)
        for ch in proc.children(recursive=True):
            ch.terminate()
        proc.terminate()
        state.remove_process(pid_str)
        typer.echo(f"Process {pid} killed.")
    except psutil.NoSuchProcess:
        state.remove_process(pid_str)
        typer.echo("Process not found. Removed from state.")


def _kill_group(processes: dict) -> None:
    for pid_str in processes:
        try:
            proc = psutil.Process(int(pid_str))
            for ch in proc.children(recursive=True):
                ch.terminate()
            proc.terminate()
            typer.echo(f"Process {pid_str} terminated.")
        except psutil.NoSuchProcess:
            typer.echo(f"Process {pid_str} not found. Removed from state.")
        except Exception as exc:
            typer.echo(f"Error terminating {pid_str}: {exc}")
