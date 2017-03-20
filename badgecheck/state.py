INITIAL_STATE = {
    'input': {},
    'graph': [],
    'tasks': []
}


def filter_active_tasks(state):
    return [t for t in state.get('tasks') if not t.get('complete')]
