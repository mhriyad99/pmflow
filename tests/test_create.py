from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from pm.main import app

runner = CliRunner()


def _mock_proc(pid=1234):
    proc = MagicMock()
    proc.pid = pid
    return proc


def test_create_happy_path(patched_state):
    with patch("pm.commands.create.subprocess.Popen", return_value=_mock_proc(1234)):
        result = runner.invoke(app, ["create", "echo hello", "--name", "greet"])
    assert result.exit_code == 0
    assert "1234" in result.output
    assert "1234" in patched_state.get_processes()


def test_create_child_requires_group(patched_state):
    with patch("pm.commands.create.subprocess.Popen", return_value=_mock_proc()):
        result = runner.invoke(app, ["create", "echo", "--relation", "child"])
    assert result.exit_code != 0
    assert "800" in result.output


def test_create_child_group_must_exist(patched_state):
    with patch("pm.commands.create.subprocess.Popen", return_value=_mock_proc()):
        result = runner.invoke(app, ["create", "echo", "--relation", "child", "--group", "nonexistent"])
    assert result.exit_code != 0
    assert "801" in result.output


def test_create_duplicate_parent_group(patched_state):
    with patch("pm.commands.create.subprocess.Popen", return_value=_mock_proc(1)):
        runner.invoke(app, ["create", "echo a", "--group", "mygroup"])
    with patch("pm.commands.create.subprocess.Popen", return_value=_mock_proc(2)):
        result = runner.invoke(app, ["create", "echo b", "--group", "mygroup"])
    assert result.exit_code != 0
    assert "802" in result.output


def test_create_with_log_file(patched_state, tmp_path):
    log = str(tmp_path / "out.log")
    with patch("pm.commands.create.subprocess.Popen", return_value=_mock_proc(9999)):
        with patch("pm.commands.create._open_log", return_value=None):
            result = runner.invoke(app, ["create", "echo hi", "--log-file", log])
    assert result.exit_code == 0
    procs = patched_state.get_processes()
    assert "9999" in procs


def test_start_is_alias_for_create(patched_state):
    with patch("pm.commands.create.subprocess.Popen", return_value=_mock_proc(5555)):
        result = runner.invoke(app, ["start", "echo alias"])
    assert result.exit_code == 0
    assert "5555" in result.output
