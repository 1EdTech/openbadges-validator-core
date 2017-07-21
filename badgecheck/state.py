import six

from .utils import list_of, MESSAGE_LEVEL_ERROR, MESSAGE_LEVEL_INFO, MESSAGE_LEVEL_WARNING

INITIAL_STATE = {
    'input': {},
    'graph': [],
    'tasks': [],
    'validationReport': {}
}


# Tasks
def filter_active_tasks(state):
    tasks = state.get('tasks')

    def _task_is_ready(task):
        # Return True if task is not complete and task has no unfulfilled prerequisites
        if task.get('complete'):
            return False

        prerequisites = list_of(task.get('prerequisites', []))
        for prereq in prerequisites:
            prereq_tasks = [pt for pt in tasks if pt.get('name') == prereq or pt.get('task_key') == prereq]
            if not prereq_tasks or not all(task.get('complete') for task in prereq_tasks):
                return False

        return True

    return [t for t in tasks if _task_is_ready(t)]


def filter_failed_tasks(state):
    return [t for t in state.get('tasks') if not t.get('success')]


# Messages
def filter_messages_for_report(state):
    messages = []
    for t in state.get('tasks'):
        if not t.get('success') or t.get('messageLevel') == MESSAGE_LEVEL_INFO:
            messages.append(t)
    return messages


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


def get_node_by_path(state, node_path):
    """
    Filter state to return first node that matches the requested id and property path.
    A path takes the format ['_:b0', 'prop_name', 1, 'another_prop_name'].
    Each entry is either a string (dict key) or non-negative integer (list index).
    :param state: state object with "graph" property as a list
    :param node_path: node path list
    Raises IndexError if no node found or no list index found.
    Raises KeyError if no property found in node.
    Raises TypeError if node next path not a string or list next path not an int.
    """
    if len(node_path) > 1:
        paths = iter(node_path)
        try:
            node_id = paths.next()
            node = get_node_by_id(state, node_id)
            while True:
                prop_name = paths.next()
                if not isinstance(prop_name, six.string_types):
                    raise TypeError(
                        'Node property {} should be a string type to use in a path'.format(prop_name))

                val = node[prop_name]

                if isinstance(val, list):
                    i = paths.next()
                    val = val[i]

                if isinstance(val, dict):
                    node = val
                    continue

                return get_node_by_path(state, [val] + list(paths))  # Recurse with remaining path
        except StopIteration:
            if isinstance(val, (dict, list)):
                return val
            raise TypeError("Node path {} not properly formed.")

    else:
        return get_node_by_id(state, node_path[0])


def node_match_exists(state, node_id):
    try:
        get_node_by_id(state, node_id)
    except IndexError:
        return False
    return True
