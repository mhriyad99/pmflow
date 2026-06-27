import shutil
from pathlib import Path

from platformdirs import user_data_dir, user_log_dir

from pm.utils import StateManager

DATA_DIR = Path(user_data_dir("pmflow"))
LOG_DIR = Path(user_log_dir("pmflow"))
STATE_FILE = DATA_DIR / "processes_state.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# One-time migration: copy state from old in-package location (pre-1.3)
_old_state = Path(__file__).parent / "processes_state.json"
if _old_state.exists() and not STATE_FILE.exists():
    try:
        shutil.copy(_old_state, STATE_FILE)
    except Exception:
        pass

state = StateManager(str(STATE_FILE))
