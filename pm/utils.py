import json
import os
import sys
from typing import List, Dict

import typer

from pm.schema import Relation

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

    def get_processes(self):
        return self.processes

    def get_parents_groupname(self) -> List[Relation]:
        parent_groups = [process_meta_data["group"] for process_meta_data in self.processes.values()
                         if process_meta_data["relation"] == Relation.PARENT]
        return parent_groups

    def get_a_group(self, group_name: str) -> Dict:
        group_process = {pid: data for pid, data in self.processes.items() if data["group"] == group_name}
        return group_process

    def is_group_exist(self, group_name: str) -> bool:
        return group_name in self.get_parents_groupname()



def load_state(path):
    """Load processes state from a file."""
    global processes
    if os.path.exists(path):
        with open(path, "r") as file:
            processes = json.load(file)

def signal_handler(sig, frame):
    typer.echo("Ctrl+C pressed. Terminating all managed processes...")
    sys.exit(0)