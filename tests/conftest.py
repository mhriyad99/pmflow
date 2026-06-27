import pytest
from pm.utils import StateBase, StateManager


@pytest.fixture(autouse=True)
def reset_singleton():
    StateBase._instance = None
    yield
    StateBase._instance = None


@pytest.fixture
def tmp_state(tmp_path):
    return StateManager(str(tmp_path / "state.json"))


@pytest.fixture
def patched_state(tmp_path, monkeypatch):
    """Return a fresh StateManager and patch it everywhere commands use it."""
    StateBase._instance = None
    sm = StateManager(str(tmp_path / "state.json"))

    import pm.settings
    import pm.commands.create
    import pm.commands.kill
    import pm.commands.ls
    import pm.commands.stop
    import pm.commands.info
    import pm.commands.logs
    import pm.commands.cleanup

    for mod in (
        pm.settings,
        pm.commands.create,
        pm.commands.kill,
        pm.commands.ls,
        pm.commands.stop,
        pm.commands.info,
        pm.commands.logs,
        pm.commands.cleanup,
    ):
        monkeypatch.setattr(mod, "state", sm)

    yield sm
