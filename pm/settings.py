import os
from pm.utils import StateManager

STATE_FILE = os.path.join(os.path.dirname(__file__), 'processes_state.json')
INSTANCE_FILE = os.path.join(os.path.dirname(__file__), 'instances.pkl')
state = StateManager(STATE_FILE)