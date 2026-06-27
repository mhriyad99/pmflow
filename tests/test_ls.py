import json
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from pm.main import app
from pm.schema import Status

runner = CliRunner()


def _add_proc(state, pid, name=None, group="g", relation="parent", status="running"):
    state.add_process(pid, {
        "command": "echo", "name": name, "group": group,
        "relation": relation, "status": status,
    })


def _mock_running_process():
    proc = MagicMock()
    proc.status.return_value = "sleeping"  # not STATUS_STOPPED
    return proc


def test_ls_empty(patched_state):
    with patch("pm.commands.ls.psutil.Process", side_effect=Exception):
        result = runner.invoke(app, ["ls"])
    assert result.exit_code == 0


def test_ls_json_output(patched_state):
    _add_proc(patched_state, 1, name="api")
    with patch("pm.commands.ls.psutil.Process", return_value=_mock_running_process()):
        result = runner.invoke(app, ["ls", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "1" in data
    assert data["1"]["name"] == "api"


def test_ls_filter_by_group(patched_state):
    _add_proc(patched_state, 1, group="backend")
    _add_proc(patched_state, 2, group="frontend")
    with patch("pm.commands.ls.psutil.Process", return_value=_mock_running_process()):
        result = runner.invoke(app, ["ls", "--json", "--group", "backend"])
    data = json.loads(result.output)
    assert "1" in data
    assert "2" not in data


def test_ls_filter_running(patched_state):
    _add_proc(patched_state, 1, status=Status.RUNNING)
    _add_proc(patched_state, 2, status=Status.STOPPED)

    import psutil as _psutil

    def side_effect(pid):
        if pid == 1:
            return _mock_running_process()
        raise _psutil.NoSuchProcess(pid)

    with patch("pm.commands.ls.psutil.Process", side_effect=side_effect):
        result = runner.invoke(app, ["ls", "--json", "--running"])
    data = json.loads(result.output)
    assert "1" in data
    assert "2" not in data


def test_ls_unknown_group(patched_state):
    result = runner.invoke(app, ["ls", "--group", "doesnotexist"])
    assert result.exit_code != 0
    assert "1000" in result.output


def test_status_is_alias_for_ls(patched_state):
    _add_proc(patched_state, 99, name="x")
    with patch("pm.commands.ls.psutil.Process", return_value=_mock_running_process()):
        result = runner.invoke(app, ["status", "--json"])
    data = json.loads(result.output)
    assert "99" in data
