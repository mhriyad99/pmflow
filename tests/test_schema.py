from pm.schema import Relation, Status, ProcessRecord


def test_relation_values():
    assert Relation.PARENT == "parent"
    assert Relation.CHILD == "child"


def test_status_values():
    assert Status.RUNNING == "running"
    assert Status.PAUSED == "paused"
    assert Status.STOPPED == "stopped"
    assert Status.CRASHED == "crashed"
    assert Status.UNKNOWN == "unknown"


def test_process_record_defaults():
    rec = ProcessRecord(pid=1, command="echo hi", name=None, group="g1", relation="parent")
    assert rec.status == Status.RUNNING
    assert rec.autostart is True
    assert rec.exit_code is None
    assert rec.log_file is None
    assert rec.exited_at is None


def test_process_record_to_dict():
    rec = ProcessRecord(pid=42, command="sleep 1", name="sleeper", group="g", relation="parent")
    d = rec.to_dict()
    assert d["pid"] == 42
    assert d["command"] == "sleep 1"
    assert d["name"] == "sleeper"


def test_process_record_from_dict_full():
    data = {
        "command": "python app.py",
        "name": "api",
        "group": "backend",
        "relation": "parent",
        "status": "running",
        "exit_code": None,
        "log_file": "/tmp/api.log",
        "autostart": False,
        "created_at": "2026-01-01T00:00:00+00:00",
        "exited_at": None,
    }
    rec = ProcessRecord.from_dict(100, data)
    assert rec.pid == 100
    assert rec.name == "api"
    assert rec.log_file == "/tmp/api.log"
    assert rec.autostart is False


def test_process_record_from_dict_sparse():
    """from_dict must handle old-format state without new fields."""
    data = {"command": "ping google.com", "name": None, "group": "g", "relation": "parent"}
    rec = ProcessRecord.from_dict(7, data)
    assert rec.pid == 7
    assert rec.autostart is True
    assert rec.status == Status.UNKNOWN
