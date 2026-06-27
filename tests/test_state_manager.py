import json
import pytest
from pm.utils import StateManager, StateBase


def test_initial_state_is_empty(tmp_state):
    assert tmp_state.get_processes() == {}


def test_add_and_get_process(tmp_state):
    tmp_state.add_process(123, {"command": "echo", "name": "test", "group": "g", "relation": "parent"})
    procs = tmp_state.get_processes()
    assert "123" in procs
    assert procs["123"]["command"] == "echo"


def test_remove_process(tmp_state):
    tmp_state.add_process(1, {"command": "x", "name": None, "group": "g", "relation": "parent"})
    tmp_state.remove_process(1)
    assert "1" not in tmp_state.get_processes()


def test_update_process(tmp_state):
    tmp_state.add_process(5, {"command": "x", "name": None, "group": "g", "relation": "parent", "status": "running"})
    tmp_state.update_process(5, "status", "stopped")
    assert tmp_state.get_processes()["5"]["status"] == "stopped"


def test_bulk_update(tmp_state):
    new_data = {
        "10": {"command": "a", "name": None, "group": "g", "relation": "parent"},
        "20": {"command": "b", "name": None, "group": "g2", "relation": "parent"},
    }
    tmp_state.bulk_update(new_data)
    assert "10" in tmp_state.get_processes()
    assert "20" in tmp_state.get_processes()


def test_remove_all(tmp_state):
    tmp_state.add_process(1, {"command": "x", "name": None, "group": "g", "relation": "parent"})
    tmp_state.add_process(2, {"command": "y", "name": None, "group": "g2", "relation": "parent"})
    tmp_state.remove_all_processes()
    assert tmp_state.get_processes() == {}


def test_persistence(tmp_path):
    StateBase._instance = None
    sm1 = StateManager(str(tmp_path / "state.json"))
    sm1.add_process(99, {"command": "sleep", "name": "s", "group": "g", "relation": "parent"})
    StateBase._instance = None
    sm2 = StateManager(str(tmp_path / "state.json"))
    assert "99" in sm2.get_processes()


def test_get_parents_groupname(tmp_state):
    tmp_state.add_process(1, {"command": "x", "name": None, "group": "alpha", "relation": "parent"})
    tmp_state.add_process(2, {"command": "y", "name": None, "group": "alpha", "relation": "child"})
    groups = tmp_state.get_parents_groupname()
    assert "alpha" in groups
    assert len(groups) == 1


def test_is_group_exist(tmp_state):
    tmp_state.add_process(1, {"command": "x", "name": None, "group": "mygroup", "relation": "parent"})
    assert tmp_state.is_group_exist("mygroup") is True
    assert tmp_state.is_group_exist("other") is False


def test_get_by_name_or_pid_by_pid(tmp_state):
    tmp_state.add_process(55, {"command": "x", "name": "worker", "group": "g", "relation": "parent"})
    result = tmp_state.get_by_name_or_pid("55")
    assert result is not None
    assert result[0] == "55"


def test_get_by_name_or_pid_by_name(tmp_state):
    tmp_state.add_process(77, {"command": "x", "name": "api", "group": "g", "relation": "parent"})
    result = tmp_state.get_by_name_or_pid("api")
    assert result is not None
    assert result[1]["name"] == "api"


def test_get_by_name_or_pid_not_found(tmp_state):
    assert tmp_state.get_by_name_or_pid("nonexistent") is None


def test_get_a_group(tmp_state):
    tmp_state.add_process(1, {"command": "a", "name": None, "group": "web", "relation": "parent"})
    tmp_state.add_process(2, {"command": "b", "name": None, "group": "web", "relation": "child"})
    tmp_state.add_process(3, {"command": "c", "name": None, "group": "db", "relation": "parent"})
    group = tmp_state.get_a_group("web")
    assert "1" in group
    assert "2" in group
    assert "3" not in group
