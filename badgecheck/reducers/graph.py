import copy

from ..actions.action_types import ADD_NODE, UPDATE_NODE

current_node_id = 0
def _get_next_blank_node_id(state):
    global current_node_id
    return "_:b{}".format(current_node_id)


def graph_reducer(state=None, action=None):
    if state is None:
        state = []

    if action.get('type') == ADD_NODE:
        state = list(state)  # copy state instead of mutating original
        new_node = copy.deepcopy(action.get('data'))
        if action.get('node_id') and action.get('data', {}).get('id') is None:
            new_node['id'] = action.get('node_id')
        if not new_node.get('id'):
            new_node['id'] = _get_next_blank_node_id(state)
        state.append(new_node)
    elif action.get('type') == UPDATE_NODE:
        # TODO
        raise NotImplementedError("TODO: Implement updating nodes.")

    return state
