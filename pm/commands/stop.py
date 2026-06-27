"""
Graceful process management: stop, restart
"""

from datetime import datetime, timezone
from typing import Optional

import typer
import psutil
from typing_extensions import Annotated

from pm.settings import state
from pm.schema import Status
from pm.errors import fmt


def _mark_exited(pid_str: str, exit_code: Optional[int]) -> None:
    final = Status.STOPPED if (exit_code is None or exit_code == 0) else Status.CRASHED
    state.update_process(pid_str, "status", final)
    state.update_process(pid_str, "exit_code", exit_code)
    state.update_process(pid_str, "exited_at", datetime.now(timezone.utc).isoformat())


def stop(
    name_or_pid: Annotated[str, typer.Argument(help="Process name or PID")],
    timeout: Annotated[int, typer.Option("--timeout", "-t", help="Seconds before SIGKILL")] = 10,
    force: Annotated[bool, typer.Option("--force", "-F", help="Skip SIGTERM, use SIGKILL")] = False,
) -> None:
    """Gracefully stop a process (SIGTERM → wait → SIGKILL). Keeps entry in state."""
    result = state.get_by_name_or_pid(name_or_pid)
    if not result:
        typer.echo(fmt(1001))
        raise typer.Exit(code=1)

    pid_str, _ = result
    pid = int(pid_str)

    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        _mark_exited(pid_str, None)
        typer.echo(f"Process {pid} was not running. Marked as stopped.")
        return

    children = proc.children(recursive=True)

    if force:
        for ch in children:
            try:
                ch.kill()
            except psutil.NoSuchProcess:
                pass
        proc.kill()
        typer.echo(f"Process {pid} killed (SIGKILL).")
    else:
        for ch in children:
            try:
                ch.terminate()
            except psutil.NoSuchProcess:
                pass
        proc.terminate()
        try:
            gone, alive = psutil.wait_procs([proc], timeout=timeout)
            if alive:
                for p in alive:
                    try:
                        p.kill()
                    except psutil.NoSuchProcess:
                        pass
                typer.echo(f"Process {pid} did not exit in {timeout}s; sent SIGKILL.")
            else:
                typer.echo(f"Process {pid} stopped gracefully.")
        except Exception:
            try:
                proc.kill()
            except psutil.NoSuchProcess:
                pass

    exit_code: Optional[int] = None
    try:
        exit_code = proc.wait(timeout=2)
    except (psutil.NoSuchProcess, psutil.TimeoutExpired):
        pass

    _mark_exited(pid_str, exit_code)


def restart(
    name_or_pid: Annotated[str, typer.Argument(help="Process name or PID")],
    timeout: Annotated[int, typer.Option("--timeout", "-t")] = 10,
) -> None:
    """Stop a process and restart it with the same command."""
    result = state.get_by_name_or_pid(name_or_pid)
    if not result:
        typer.echo(fmt(1001))
        raise typer.Exit(code=1)

    old_pid_str, data = result

    stop(name_or_pid, timeout=timeout)

    from pm.commands.create import _create_process
    pid, _ = _create_process(
        command=data["command"],
        name=data.get("name"),
        group=data.get("group"),
        relation=data.get("relation", "parent"),
        log_file=data.get("log_file"),
        autostart=data.get("autostart", True),
    )
    state.remove_process(old_pid_str)
    typer.echo(f"Process restarted. New PID: {pid}")
