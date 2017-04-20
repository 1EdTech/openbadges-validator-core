from .utils import cast_as_list

INITIAL_STATE = {
    'input': {},
    'graph': [],
    'tasks': []
}


# Tasks
def filter_active_tasks(state):
    tasks = state.get('tasks')

    def _task_is_ready(task):
        # Return True if task is not complete and task has no unfulfilled prerequisites
        if task.get('complete'):
            return False

        prerequisites = cast_as_list(task.get('prerequisites', []))
        for prereq in prerequisites:
            prereq_tasks = [pt for pt in tasks if pt.get('name') == prereq]
            if not prereq_tasks or not all(task.get('complete') for task in prereq_tasks):
                return False

        return True

    return [t for t in tasks if _task_is_ready(t)]


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
