import os
from pm.utils import StateManager

STATE_FILE = os.path.join(os.path.dirname(__file__), 'processes_state.json')
state = StateManager(STATE_FILE)