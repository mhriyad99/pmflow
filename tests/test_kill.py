from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from pm.main import app

runner = CliRunner()


def _add_proc(state, pid, name=None, group="g", relation="parent"):
    state.add_process(pid, {
        "command": "echo", "name": name, "group": group,
        "relation": relation, "status": "running",
    })


def _mock_process(pid):
    proc = MagicMock()
    proc.pid = pid
    proc.children.return_value = []
    return proc


def test_kill_requires_argument(patched_state):
    result = runner.invoke(app, ["kill"])
    assert result.exit_code != 0
    assert "1100" in result.output


def test_kill_only_one_argument(patched_state):
    result = runner.invoke(app, ["kill", "123", "--all"])
    assert result.exit_code != 0
    assert "1200" in result.output


def test_kill_by_pid(patched_state):
    _add_proc(patched_state, 100)
    with patch("pm.commands.kill.psutil.Process", return_value=_mock_process(100)):
        result = runner.invoke(app, ["kill", "100"])
    assert result.exit_code == 0
    assert "100" not in patched_state.get_processes()


def test_kill_unmanaged_pid(patched_state):
    result = runner.invoke(app, ["kill", "9999"])
    assert "not managed" in result.output.lower()


def test_kill_all(patched_state):
    _add_proc(patched_state, 1)
    _add_proc(patched_state, 2, group="g2")
    with patch("pm.commands.kill.psutil.Process", return_value=_mock_process(1)):
        result = runner.invoke(app, ["kill", "--all"])
    assert result.exit_code == 0
    assert patched_state.get_processes() == {}


def test_kill_group(patched_state):
    _add_proc(patched_state, 10, group="team")
    _add_proc(patched_state, 11, group="team", relation="child")
    _add_proc(patched_state, 12, group="other")
    with patch("pm.commands.kill.psutil.Process", return_value=_mock_process(10)):
        result = runner.invoke(app, ["kill", "--group", "team"])
    assert result.exit_code == 0
    assert "10" not in patched_state.get_processes()
    assert "11" not in patched_state.get_processes()
    assert "12" in patched_state.get_processes()
