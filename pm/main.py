#!/usr/bin/env python3
import typer

from pm.commands.create import create, recreate, respawn
from pm.commands.kill import pause, kill
from pm.commands.ls import ls

app = typer.Typer()

@app.command()
def greet(name: str):
    print(f"Hello, {name}!")


# Commands related to initiation of a process
app.command()(create)
app.command()(recreate)
app.command()(respawn)

# Commands related to deletion of a process
app.command()(pause)
app.command()(kill)


# Commands related to process presentation
app.command()(ls)


if __name__ == "__main__":
    app()
