import json
import os
import sys

import typer


def load_state(file_path):
    """Load processes state from a file."""
    global processes
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            processes = json.load(file)

def signal_handler(sig, frame):
    typer.echo("Ctrl+C pressed. Terminating all managed processes...")
    sys.exit(0)