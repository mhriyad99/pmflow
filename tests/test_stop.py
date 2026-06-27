from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from pm.main import app
from pm.schema import Status

runner = CliRunner()


def _add_proc(state, pid, name="worker", group="g"):
    state.add_process(pid, {
        "command": "echo", "name": name, "group": group,
        "relation": "parent", "status": Status.RUNNING,
        "log_file": None, "autostart": True,
    })


def _mock_process(exit_code=0):
    proc = MagicMock()
    proc.children.return_value = []
    proc.wait.return_value = exit_code
    psutil_wait_procs_result = ([proc], [])
    return proc, psutil_wait_procs_result


def test_stop_unknown_process(patched_state):
    result = runner.invoke(app, ["stop", "nobody"])
    assert result.exit_code != 0
    assert "1001" in result.output


def test_stop_by_name_graceful(patched_state):
    _add_proc(patched_state, 200, name="worker")
    proc, wait_result = _mock_process(0)

    with patch("pm.commands.stop.psutil.Process", return_value=proc):
        with patch("pm.commands.stop.psutil.wait_procs", return_value=wait_result):
            result = runner.invoke(app, ["stop", "worker"])

    assert result.exit_code == 0
    proc.terminate.assert_called_once()
    data = patched_state.get_processes().get("200", {})
    assert data.get("status") == Status.STOPPED


def test_stop_by_pid(patched_state):
    _add_proc(patched_state, 300, name="api")
    proc, wait_result = _mock_process(0)

    with patch("pm.commands.stop.psutil.Process", return_value=proc):
        with patch("pm.commands.stop.psutil.wait_procs", return_value=wait_result):
            result = runner.invoke(app, ["stop", "300"])

    assert result.exit_code == 0


def test_stop_force(patched_state):
    _add_proc(patched_state, 400, name="force-me")
    proc, _ = _mock_process()

    with patch("pm.commands.stop.psutil.Process", return_value=proc):
        result = runner.invoke(app, ["stop", "force-me", "--force"])

    assert result.exit_code == 0
    proc.kill.assert_called()


def test_stop_crashed_marks_crashed(patched_state):
    _add_proc(patched_state, 500, name="crasher")
    proc, wait_result = _mock_process(exit_code=1)

    with patch("pm.commands.stop.psutil.Process", return_value=proc):
        with patch("pm.commands.stop.psutil.wait_procs", return_value=wait_result):
            runner.invoke(app, ["stop", "crasher"])

    data = patched_state.get_processes().get("500", {})
    assert data.get("status") == Status.CRASHED
    assert data.get("exit_code") == 1


def test_stop_already_dead(patched_state):
    import psutil as _psutil
    _add_proc(patched_state, 600, name="ghost")

    with patch("pm.commands.stop.psutil.Process", side_effect=_psutil.NoSuchProcess(600)):
        result = runner.invoke(app, ["stop", "ghost"])

    assert result.exit_code == 0
    assert "stopped" in result.output.lower()
