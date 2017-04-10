INITIAL_STATE = {
    'input': {},
    'graph': [],
    'tasks': []
}


# Tasks
def filter_active_tasks(state):
    return [t for t in state.get('tasks') if not t.get('complete')]


def filter_failed_tasks(state):
    return [t for t in state.get('tasks') if not t.get('success')]


# Graph
def get_node_by_id(state, node_id):
    """
    Filter state to return first node that matches the requested id.
    :param state: state object with "graph" property as a list
    :param node_id: IRI-format string
    Raises IndexError if no node found.
    """
    return [node for node in state['graph'] if node.get('id') == node_id][0]
