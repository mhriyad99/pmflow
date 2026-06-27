import json
import os
from typing import List, Dict, Optional, Tuple

from pm.schema import Relation


class StateBase:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


class StateManager(StateBase):

    def __init__(self, state_file: str):
        self.STATE_FILE = state_file
        self.processes: Dict = {}
        self.load_state()

    def load_state(self):
        if not os.path.exists(self.STATE_FILE):
            os.makedirs(os.path.dirname(self.STATE_FILE), exist_ok=True)
            with open(self.STATE_FILE, "w") as f:
                json.dump({}, f)

        with open(self.STATE_FILE, "r") as f:
            self.processes = json.load(f)

    def save(self):
        with open(self.STATE_FILE, "w") as f:
            json.dump(self.processes, f, indent=2)

    def add_process(self, pid, data: dict):
        self.processes[str(pid)] = data
        self.save()

    def remove_process(self, pid):
        self.processes.pop(str(pid), None)
        self.save()

    def remove_all_processes(self):
        self.processes = {}
        self.save()

    def update_process(self, pid, key: str, value):
        pid_str = str(pid)
        if pid_str in self.processes:
            self.processes[pid_str][key] = value
            self.save()

    def bulk_update(self, bulk_data: dict):
        self.processes = bulk_data
        self.save()

    def get_processes(self) -> Dict:
        return self.processes

    def get_parents_groupname(self) -> List[str]:
        return [
            data["group"]
            for data in self.processes.values()
            if data.get("relation") == Relation.PARENT
        ]

    def get_a_group(self, group_name: str) -> Dict:
        return {
            pid: data
            for pid, data in self.processes.items()
            if data.get("group") == group_name
        }

    def get_by_name_or_pid(self, name_or_pid: str) -> Optional[Tuple[str, dict]]:
        """Return (pid_str, data) for the first match by PID or name, or None."""
        if name_or_pid in self.processes:
            return name_or_pid, self.processes[name_or_pid]
        for pid, data in self.processes.items():
            if data.get("name") == name_or_pid:
                return pid, data
        return None

    def is_exist(self, pid: str) -> bool:
        return str(pid) in self.processes

    def is_group_exist(self, group_name: str) -> bool:
        return group_name in self.get_parents_groupname()
