import json
import os
import sys

import typer


class StateManager:
    def __init__(self, STATE_FILE):
        self.processes = {}
        self.STATE_FILE = STATE_FILE
        self.load_state()

    def load_state(self):

        if not os.path.exists(self.STATE_FILE):
            with open(self.STATE_FILE, "w") as file:
                json.dump({}, file)
                print("Created new state file")

        with open(self.STATE_FILE, "r") as file:
            self.processes = json.load(file)

    def save(self):
        with open(self.STATE_FILE, "w") as file:
            json.dump(self.processes, file)

    def get_processes(self):
        return self.processes

    def add_process(self, pid, data):
        self.processes[str(pid)] = data
        self.save()

    def remove_process(self, pid):
        self.processes.pop(str(pid), None)
        self.save()

    def remove_all_processes(self):
        self.processes = {}
        self.save()

    def update_process(self, pid, key, value):
        self.processes[str(pid)][key] = value
        self.save()

    def bulk_update(self, bulk_data):
        self.processes = bulk_data
        self.save()



def load_state(path):
    """Load processes state from a file."""
    global processes
    if os.path.exists(path):
        with open(path, "r") as file:
            processes = json.load(file)

def signal_handler(sig, frame):
    typer.echo("Ctrl+C pressed. Terminating all managed processes...")
    sys.exit(0)