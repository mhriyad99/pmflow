#!/usr/bin/env python3
from importlib.metadata import version as pkg_version

import typer

from pm.commands.create import create, recreate, respawn
from pm.commands.kill import pause, kill
from pm.commands.ls import ls
from pm.commands.stop import stop, restart
from pm.commands.info import info
from pm.commands.logs import logs
from pm.commands.cleanup import cleanup
from pm.commands.manage import up, down

app = typer.Typer(help="PMFlow — lightweight process manager")

# Creation
app.command("create")(create)
app.command("start")(create)      # alias
app.command("recreate")(recreate)
app.command("respawn")(respawn)

# Graceful stop / restart
app.command("stop")(stop)
app.command("restart")(restart)

# Immediate termination
app.command("pause")(pause)
app.command("kill")(kill)

# Inspection
app.command("ls")(ls)
app.command("status")(ls)         # alias
app.command("info")(info)
app.command("logs")(logs)

# Maintenance
app.command("cleanup")(cleanup)

# Config-file multi-process
app.command("up")(up)
app.command("down")(down)


@app.command("version")
def version() -> None:
    """Show pmflow version."""
    try:
        v = pkg_version("pmflow")
    except Exception:
        v = "unknown"
    typer.echo(f"pmflow {v}")


if __name__ == "__main__":
    app()
