"""
Config-file based multi-process management: up, down
Reads pmflow.yaml in the current working directory.
"""

from pathlib import Path
from typing import Optional

import typer
import yaml
from typing_extensions import Annotated

from pm.settings import state
from pm.errors import fmt


def up(
    config: Annotated[str, typer.Option("--config", "-c")] = "pmflow.yaml",
) -> None:
    """Start all processes defined in pmflow.yaml."""
    config_path = Path(config)
    if not config_path.exists():
        typer.echo(fmt(1400))
        raise typer.Exit(code=1)

    try:
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
    except Exception as exc:
        typer.echo(f"{fmt(1401)}: {exc}")
        raise typer.Exit(code=1)

    processes = cfg.get("processes", {})
    if not processes:
        typer.echo("No processes defined in pmflow.yaml.")
        return

    # Start parents before children so group validation passes
    ordered = sorted(
        processes.items(),
        key=lambda x: (x[1].get("relation", "parent") == "child", x[0]),
    )

    from pm.commands.create import _create_process

    for name, proc_cfg in ordered:
        command = proc_cfg.get("command")
        if not command:
            typer.echo(f"Skipping '{name}': no command defined.")
            continue
        try:
            pid, _ = _create_process(
                command=command,
                name=name,
                group=proc_cfg.get("group"),
                relation=proc_cfg.get("relation", "parent"),
                log_file=proc_cfg.get("log_file"),
                autostart=proc_cfg.get("autostart", True),
            )
            typer.echo(f"Started '{name}' with PID {pid}")
        except SystemExit:
            typer.echo(f"Failed to start '{name}'.")


def down(
    config: Annotated[str, typer.Option("--config", "-c")] = "pmflow.yaml",
) -> None:
    """Stop all processes defined in pmflow.yaml."""
    config_path = Path(config)
    if not config_path.exists():
        typer.echo(fmt(1400))
        raise typer.Exit(code=1)

    try:
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
    except Exception as exc:
        typer.echo(f"{fmt(1401)}: {exc}")
        raise typer.Exit(code=1)

    from pm.commands.stop import stop

    for name in cfg.get("processes", {}):
        if state.get_by_name_or_pid(name):
            typer.echo(f"Stopping '{name}'...")
            stop(name)
        else:
            typer.echo(f"Process '{name}' not found in state.")
