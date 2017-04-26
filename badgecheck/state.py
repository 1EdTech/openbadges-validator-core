from .utils import cast_as_list

INITIAL_STATE = {
    'input': {},
    'graph': [],
    'tasks': []
}

MESSAGE_LEVEL_ERROR = 'ERROR'
MESSAGE_LEVEL_WARNING = 'WARNING'
MESSAGE_LEVEL_INFO = 'INFO'
MESSAGE_LEVELS = (MESSAGE_LEVEL_ERROR, MESSAGE_LEVEL_WARNING, MESSAGE_LEVEL_INFO,)


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


# Messages
def format_message(task_meta):
    ret = {
        'name': task_meta.get('name'),
        'success': task_meta.get('success', False),
        'result': task_meta.get('result', ''),
        'messageLevel': task_meta.get('messageLevel', MESSAGE_LEVEL_ERROR),
    }
    if task_meta.get('node_id'):
        ret['node_id'] = task_meta['node_id']
    if task_meta.get('prop_name'):
        ret['prop_name'] = task_meta['prop_name']
    if not task_meta.get('complete') and not ret['result']:
        ret['result'] = 'Task could not execute.'

    return ret


# Graph
def get_node_by_id(state, node_id):
    """
    Filter state to return first node that matches the requested id.
    :param state: state object with "graph" property as a list
    :param node_id: IRI-format string
    Raises IndexError if no node found.
    """
    return [node for node in state['graph'] if node.get('id') == node_id][0]
